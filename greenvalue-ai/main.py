# ============================================================
# GreenValue AI Engine — FastAPI Application Entry Point
# ============================================================
#
#   uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
#
# ============================================================

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from io import BytesIO

from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List

from config.settings import get_settings
from modules.vision.inference import get_inference_engine
from modules.storage.minio_client import get_storage_service
from modules.queue.consumer import get_queue_consumer
from modules.pipeline import AnalysisPipeline

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("greenvalue-ai")

settings = get_settings()

# ── Shared State ─────────────────────────────────────────────
_state: dict = {
    "start_time": None,
    "pipeline": None,
    "queue_task": None,
}


# ── Lifespan ─────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    logger.info("=" * 60)
    logger.info("  GreenValue AI Engine — Starting up")
    logger.info("=" * 60)
    _state["start_time"] = time.time()

    # 1. Load YOLO model (heavy — do once)
    engine = get_inference_engine()
    engine.load_model()
    logger.info(f"YOLO model loaded on {engine.device}")

    # 2. MinIO bucket check
    try:
        storage = get_storage_service()
        storage.connect()
        logger.info("RustFS (S3) connection OK — buckets verified")
    except Exception as e:
        logger.warning(f"MinIO not available (will retry lazily): {e}")

    # 3. Instantiate pipeline
    _state["pipeline"] = AnalysisPipeline()

    # 4. Start background queue consumer
    try:
        consumer = get_queue_consumer()
        await consumer.connect()

        pipeline = _state["pipeline"]

        async def _job_handler(job_id: str, data: dict) -> dict:
            return await pipeline.run(
                job_id=job_id,
                file_key=data.get("fileKey", data.get("file_key", "")),
                property_id=data.get("propertyId", data.get("property_id", "")),
                model_size=data.get("modelSize"),
            )

        consumer.register_handler(_job_handler)
        _state["queue_task"] = asyncio.create_task(consumer.start_consuming())
        logger.info("Queue consumer started (listening for BullMQ jobs)")
    except Exception as e:
        logger.warning(f"Queue consumer not started: {e}")

    logger.info("=" * 60)
    logger.info("  GreenValue AI Engine — READY")
    logger.info("=" * 60)

    yield  # ── app is running ──

    # Shutdown
    logger.info("Shutting down GreenValue AI Engine …")
    if _state["queue_task"] and not _state["queue_task"].done():
        _state["queue_task"].cancel()
        try:
            await _state["queue_task"]
        except asyncio.CancelledError:
            pass
    logger.info("Shutdown complete.")


# ── App ──────────────────────────────────────────────────────
app = FastAPI(
    title="GreenValue AI Engine",
    description="YOLO11-powered building component detection, U-Value analysis, and energy labelling.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic Schemas ─────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    model_loaded: bool
    model_version: str
    device: str
    gpu_info: Optional[dict] = None


class AnalyzeRequest(BaseModel):
    file_key: str = Field(..., description="MinIO object key for the source image")
    property_id: str = Field(..., description="Property UUID")
    model_size: Optional[str] = Field(None, description="YOLO model size (n/s/m/l/x)")


class AnalyzeResponse(BaseModel):
    job_id: str
    status: str
    message: str


class UValueRequest(BaseModel):
    component_type: str = Field(..., description="Component type: facade, roof, window, door")
    material: Optional[str] = Field(None, description="Material key from material database")
    thickness_m: Optional[float] = Field(None, description="Material thickness in meters")
    building_year: Optional[int] = Field(None, description="Construction year")


# ── Health ───────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """System health and model readiness status."""
    engine = get_inference_engine()
    uptime = time.time() - _state["start_time"] if _state["start_time"] else 0.0

    return HealthResponse(
        status="healthy",
        uptime_seconds=round(uptime, 1),
        model_loaded=engine.model is not None,
        model_version=engine.model_version or "not loaded",
        device=str(engine.device),
        gpu_info=engine.gpu_info,
    )


@app.get("/", tags=["health"])
async def root():
    return {"service": "greenvalue-ai", "status": "running"}


# ── Analyze (queue-based) ───────────────────────────────────
@app.post("/api/v1/analyze", response_model=AnalyzeResponse, tags=["analysis"])
async def submit_analysis(body: AnalyzeRequest):
    """
    Submit an analysis job.
    The image is fetched from MinIO and results are stored for retrieval.
    For production: pushes to BullMQ and returns the job ID.
    For dev/testing: runs synchronously and returns job_id.
    """
    job_id = str(uuid.uuid4())

    # Run synchronously for now (in production, push to Redis queue)
    try:
        pipeline: AnalysisPipeline = _state["pipeline"]
        result = await pipeline.run(
            job_id=job_id,
            file_key=body.file_key,
            property_id=body.property_id,
            model_size=body.model_size,
        )
        # Store result in app state (production would put in Redis/DB)
        _state.setdefault("results", {})[job_id] = result
        return AnalyzeResponse(
            job_id=job_id,
            status="completed",
            message=f"Analysis completed. Energy label: {result['physics']['energy_label']}",
        )
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Quick Analyze (direct upload) ───────────────────────────
@app.post("/api/v1/analyze/upload", tags=["analysis"])
async def analyze_upload(file: UploadFile = File(...)):
    """
    Quick analysis — upload an image directly (no MinIO).
    Useful for testing and demo purposes.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    image_bytes = await file.read()
    if len(image_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 20MB)")

    pipeline: AnalysisPipeline = _state["pipeline"]
    try:
        result = await pipeline.analyze_image_only(image_bytes)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Upload analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Get Result ──────────────────────────────────────────────
@app.get("/api/v1/analyze/{job_id}", tags=["analysis"])
async def get_analysis_result(job_id: str):
    """Retrieve a completed analysis result by job ID."""
    results = _state.get("results", {})
    if job_id not in results:
        raise HTTPException(status_code=404, detail="Job not found")
    return results[job_id]


# ── U-Value Calculator ──────────────────────────────────────
@app.post("/api/v1/u-value", tags=["physics"])
async def calculate_u_value(body: UValueRequest):
    """Calculate U-Value for a building component."""
    from modules.physics.u_value import PhysicsEngine

    physics = PhysicsEngine()
    try:
        result = physics.calculate_u_value(
            component_type=body.component_type,
            material=body.material,
            thickness_m=body.thickness_m,
            building_year=body.building_year,
        )
        return result
    except Exception as e:
        logger.error(f"U-Value calculation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ── Materials Database ──────────────────────────────────────
@app.get("/api/v1/materials", tags=["physics"])
async def list_materials():
    """List available materials in the physics engine database."""
    from modules.physics.u_value import PhysicsEngine

    physics = PhysicsEngine()
    return {
        "materials": physics.MATERIAL_CONDUCTIVITY,
        "component_types": list(physics.STANDARD_U_VALUES.keys()),
    }


# ── Model Info ──────────────────────────────────────────────
@app.get("/api/v1/model/info", tags=["model"])
async def model_info():
    """Get information about the currently loaded YOLO model."""
    engine = get_inference_engine()
    return {
        "model_loaded": engine.model is not None,
        "model_version": engine.model_version,
        "model_path": str(engine.model_path),
        "device": str(engine.device),
        "gpu_info": engine.gpu_info,
        "input_size": settings.yolo_img_size,
        "confidence_threshold": settings.yolo_conf_threshold,
        "classes": engine.CLASS_NAMES,
    }


# ── Metrics (Prometheus) ────────────────────────────────────
from starlette.responses import Response


@app.get("/metrics", tags=["monitoring"])
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint (text/plain format)."""
    engine = get_inference_engine()
    uptime = time.time() - _state["start_time"] if _state["start_time"] else 0

    lines = [
        "# HELP greenvalue_up Service availability",
        "# TYPE greenvalue_up gauge",
        "greenvalue_up 1",
        "",
        "# HELP greenvalue_uptime_seconds Uptime in seconds",
        "# TYPE greenvalue_uptime_seconds gauge",
        f"greenvalue_uptime_seconds {uptime:.1f}",
        "",
        "# HELP greenvalue_model_loaded YOLO model loaded status",
        "# TYPE greenvalue_model_loaded gauge",
        f"greenvalue_model_loaded {1 if engine.model is not None else 0}",
        "",
        "# HELP greenvalue_jobs_completed_total Total completed analysis jobs",
        "# TYPE greenvalue_jobs_completed_total counter",
        f'greenvalue_jobs_completed_total {len(_state.get("results", {}))}',
        "",
    ]
    return Response(content="\n".join(lines) + "\n", media_type="text/plain")


# =============================================================================
# RAG MODULE ENDPOINTS
# Retrieval-Augmented Generation for property knowledge base
# =============================================================================

class RAGQueryRequest(BaseModel):
    question: str = Field(..., description="Question to ask the knowledge base")
    category: Optional[str] = Field(None, description="Category filter (Real Estate, Sustainability, etc)")
    user_id: Optional[str] = Field("default", description="User ID for personalization")


class RAGQueryResponse(BaseModel):
    answer: str
    query_id: int
    sources: List[dict]
    route: dict


class RAGIngestResponse(BaseModel):
    files_processed: int
    total_child_chunks: int
    total_parent_chunks: int


# Lazy RAG instance
_rag_instance = None


def get_rag_instance():
    """Get or create RAG instance (lazy loading)."""
    global _rag_instance
    if _rag_instance is None:
        try:
            from modules.rag import GreenValueRAG
            _rag_instance = GreenValueRAG()
            _rag_instance.initialize()
            logger.info("RAG module initialized")
        except Exception as e:
            logger.error(f"RAG initialization failed: {e}")
            raise HTTPException(status_code=503, detail=f"RAG not available: {e}")
    return _rag_instance


@app.post("/api/v1/rag/query", response_model=RAGQueryResponse, tags=["rag"])
async def rag_query(body: RAGQueryRequest):
    """
    Query the property knowledge base using RAG.
    Returns answer with sources and routing metadata.
    """
    try:
        rag = get_rag_instance()
        result = rag.query(
            question=body.question,
            category=body.category,
            user_id=body.user_id or "default",
        )
        return RAGQueryResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/rag/ingest", tags=["rag"])
async def rag_ingest(force_recreate: bool = Query(False, description="Force recreate collections")):
    """
    Ingest PDF documents from knowledge base directory.
    Set force_recreate=true to rebuild from scratch.
    """
    try:
        rag = get_rag_instance()
        result = rag.build_knowledge_base(force_recreate=force_recreate)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/rag/ingest/file", tags=["rag"])
async def rag_ingest_file(file: UploadFile = File(...)):
    """
    Ingest a single PDF file into the knowledge base.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        import tempfile
        import os
        
        # Save to temp file
        content = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            rag = get_rag_instance()
            result = rag.ingest_document(tmp_path)
            return result
        finally:
            os.unlink(tmp_path)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG file ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/rag/status", tags=["rag"])
async def rag_status():
    """Get RAG system status and collection statistics."""
    try:
        rag = get_rag_instance()
        return rag.get_status()
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "not_initialized", "error": str(e)}


@app.post("/api/v1/rag/feedback", tags=["rag"])
async def rag_feedback(
    query_id: int = Query(..., description="Query ID from previous response"),
    helpful: bool = Query(..., description="Was the response helpful?"),
    feedback_text: Optional[str] = Query(None, description="Optional feedback text")
):
    """Submit feedback for a RAG query to improve future responses."""
    try:
        rag = get_rag_instance()
        rag.add_feedback(query_id, helpful, feedback_text)
        return {"status": "feedback_recorded", "query_id": query_id}
    except Exception as e:
        logger.error(f"RAG feedback failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# VISION-RAG INTEGRATION — Image Analysis + RAG
# For mobile app image uploads with AI-powered property analysis
# =============================================================================

class VisionRAGRequest(BaseModel):
    property_id: Optional[str] = Field(None, description="Property UUID for context")
    user_id: Optional[str] = Field("default", description="User ID for personalization")
    include_rag_insights: bool = Field(True, description="Include RAG-based recommendations")


class VisionRAGResponse(BaseModel):
    job_id: str
    vision_analysis: dict
    rag_insights: Optional[dict] = None
    combined_report: dict
    detections_count: int
    inefficiencies_found: List[str]


# Lazy Vision-RAG instance
_vision_rag_instance = None


def get_vision_rag_instance():
    """Get or create Vision-RAG instance (lazy loading)."""
    global _vision_rag_instance
    if _vision_rag_instance is None:
        try:
            from modules.rag import MultiModalRAGPipeline
            
            # Get or create RAG system for knowledge base queries
            rag_system = None
            try:
                rag_system = get_rag_instance()
            except Exception as e:
                logger.warning(f"RAG system not available for Vision-RAG: {e}")
            
            _vision_rag_instance = MultiModalRAGPipeline(
                rag_system=rag_system,
                cv_service_url="http://localhost:8000"
            )
            _vision_rag_instance.initialize()
            logger.info("Vision-RAG module initialized")
        except Exception as e:
            logger.error(f"Vision-RAG initialization failed: {e}")
            raise HTTPException(status_code=503, detail=f"Vision-RAG not available: {e}")
    return _vision_rag_instance


@app.post("/api/v1/vision-rag/analyze", response_model=VisionRAGResponse, tags=["vision-rag"])
async def vision_rag_analyze(
    file: UploadFile = File(..., description="Property image to analyze"),
    property_id: Optional[str] = Query(None, description="Property UUID"),
    user_id: Optional[str] = Query("default", description="User ID"),
    include_rag_insights: bool = Query(True, description="Include RAG recommendations")
):
    """
    Vision-RAG Analysis for Mobile App
    
    Upload a property image and receive:
    - YOLO11 detection results (windows, doors, facade, roof, etc.)
    - Energy efficiency analysis and deficiencies
    - Cost estimates for improvements
    - RAG-powered recommendations from knowledge base
    - Combined multi-modal report
    
    Perfect for mobile app integration.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Read image
        image_bytes = await file.read()
        if len(image_bytes) > 20 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image too large (max 20MB)")
        
        job_id = str(uuid.uuid4())
        
        # Get Vision-RAG pipeline
        vision_rag = get_vision_rag_instance()
        
        # Run multi-modal analysis
        result = await asyncio.to_thread(
            vision_rag.analyze_image_with_rag,
            image_bytes=image_bytes,
            property_id=property_id or job_id,
            user_id=user_id,
            include_rag=include_rag_insights
        )
        
        # Extract key information for response
        vision_data = result.get("vision_analysis", {})
        rag_data = result.get("rag_insights") if include_rag_insights else None
        report = result.get("combined_report", {})
        
        # Build response
        response = VisionRAGResponse(
            job_id=job_id,
            vision_analysis=vision_data,
            rag_insights=rag_data,
            combined_report=report,
            detections_count=len(vision_data.get("detections", [])),
            inefficiencies_found=vision_data.get("inefficiencies", [])
        )
        
        # Store result for later retrieval
        _state.setdefault("vision_rag_results", {})[job_id] = result
        
        logger.info(f"Vision-RAG analysis complete: {job_id} ({len(vision_data.get('detections', []))} detections)")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vision-RAG analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/vision-rag/result/{job_id}", tags=["vision-rag"])
async def get_vision_rag_result(job_id: str):
    """Retrieve a completed Vision-RAG analysis result by job ID."""
    results = _state.get("vision_rag_results", {})
    if job_id not in results:
        raise HTTPException(status_code=404, detail="Analysis result not found")
    return results[job_id]


