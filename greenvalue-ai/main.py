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
from pydantic import BaseModel, Field, model_validator
from typing import Dict, Optional, List

from config.settings import get_settings
from modules.vision.inference import get_inference_engine
from modules.storage.minio_client import get_storage_service
from modules.queue.consumer import get_queue_consumer
from modules.pipeline import AnalysisPipeline
from modules.physics.u_value import PhysicsEngine

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
    "grpc_server": None,
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

    # 5. Start gRPC server
    try:
        from modules.grpc_server.server import create_grpc_server
        grpc_port = settings.grpc_port
        grpc_server = create_grpc_server(
            pipeline=_state["pipeline"],
            inference_engine=engine,
            physics_engine=PhysicsEngine(),
            port=grpc_port,
        )
        grpc_server.start()
        _state["grpc_server"] = grpc_server
        logger.info(f"gRPC server started on port {grpc_port}")
    except Exception as e:
        logger.warning(f"gRPC server not started: {e}")

    logger.info("=" * 60)
    logger.info("  GreenValue AI Engine — READY")
    logger.info("=" * 60)

    yield  # ── app is running ──

    # Shutdown
    logger.info("Shutting down GreenValue AI Engine …")
    if _state["grpc_server"]:
        _state["grpc_server"].stop(grace=5)
        logger.info("gRPC server stopped")
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

    @model_validator(mode='before')
    @classmethod
    def normalize_field_names(cls, values):
        """Accept 'image_key' as an alias for 'file_key' (backward compat)."""
        if isinstance(values, dict):
            if 'image_key' in values and 'file_key' not in values:
                values['file_key'] = values.pop('image_key')
            # Also accept 'user_id' silently (sent by older backends)
            values.pop('user_id', None)
        return values


class AnalyzeResponse(BaseModel):
    job_id: str
    status: str
    message: str


class UValueRequest(BaseModel):
    component_type: str = Field(..., description="Component type: facade, roof, window, door")
    material: Optional[str] = Field(None, description="Material key from material database")
    thickness_mm: Optional[float] = Field(None, description="Material thickness in millimeters")
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
            material=body.material or body.component_type,
            thickness_mm=body.thickness_mm or 0.0,
            year_installed=body.building_year,
        )
        return {"u_value": result, "component_type": body.component_type, "material": body.material, "thickness_mm": body.thickness_mm, "building_year": body.building_year}
    except Exception as e:
        logger.error(f"U-Value calculation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ── Materials Database ──────────────────────────────────────
@app.get("/api/v1/materials", tags=["physics"])
async def list_materials():
    """List available materials in the physics engine database."""
    from modules.physics.u_value import PhysicsEngine, THERMAL_CONDUCTIVITY, STANDARD_UVALUES

    return {
        "materials": THERMAL_CONDUCTIVITY,
        "component_types": list(STANDARD_UVALUES.keys()),
    }


# ── Model Info ──────────────────────────────────────────────
@app.get("/api/v1/model/info", tags=["model"])
async def model_info():
    """Get information about the currently loaded YOLO model."""
    from modules.vision.inference import COMPONENT_CLASSES
    engine = get_inference_engine()
    return {
        "model_loaded": engine.model is not None,
        "model_version": engine.model_version,
        "model_path": str(engine.model_path),
        "device": str(engine.device),
        "gpu_info": engine.gpu_info,
        "input_size": settings.yolo_model_size,
        "confidence_threshold": settings.yolo_confidence_threshold,
        "classes": COMPONENT_CLASSES,
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
                cv_service_url=settings.cv_service_url
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


# =============================================================================
# OCR MODULE ENDPOINTS
# Professional OCR Engine with hi_res, tesseract, hybrid, and fast strategies
# =============================================================================

class OCRProcessRequest(BaseModel):
    strategy: Optional[str] = Field("hi_res", description="OCR strategy: hi_res, tesseract, hybrid, fast")
    languages: Optional[str] = Field(None, description="Comma-separated language codes (e.g. 'eng,tur,deu')")
    page_start: Optional[int] = Field(None, description="Start page (1-indexed)")
    page_end: Optional[int] = Field(None, description="End page (1-indexed, inclusive)")


# Lazy OCR engine instance
_ocr_engine_instance = None


def _get_ocr_engine():
    """Get or create OCR engine (lazy loading)."""
    global _ocr_engine_instance
    if _ocr_engine_instance is None:
        try:
            from modules.ocr import OCREngine
            _ocr_engine_instance = OCREngine()
            _ocr_engine_instance.initialize()
            logger.info("OCR Engine initialized for API")
        except Exception as e:
            logger.error(f"OCR Engine initialization failed: {e}")
            raise HTTPException(status_code=503, detail=f"OCR Engine not available: {e}")
    return _ocr_engine_instance


@app.post("/api/v1/ocr/process", tags=["ocr"])
async def ocr_process(
    file: UploadFile = File(..., description="PDF or image file to process"),
    strategy: str = Query("hi_res", description="OCR strategy: hi_res, tesseract, hybrid, fast"),
    languages: Optional[str] = Query(None, description="Comma-separated language codes"),
    page_start: Optional[int] = Query(None, description="Start page (1-indexed)"),
    page_end: Optional[int] = Query(None, description="End page (1-indexed, inclusive)"),
):
    """
    Professional OCR Processing

    Upload a PDF or image and extract text, tables, and images using
    the selected OCR strategy.

    Strategies:
    - **hi_res**: Unstructured API — best for tables, images, headers (primary)
    - **tesseract**: Local Tesseract OCR — best for scanned docs, multi-language
    - **hybrid**: hi_res + Tesseract cross-validation — maximum accuracy
    - **fast**: PyPDF2 text extraction — fastest, no OCR
    """
    try:
        from modules.ocr import OCREngine, OCRStrategy
        import tempfile, os

        ocr_engine = _get_ocr_engine()

        strategy_map = {
            "hi_res": OCRStrategy.HI_RES,
            "tesseract": OCRStrategy.TESSERACT,
            "hybrid": OCRStrategy.HYBRID,
            "fast": OCRStrategy.FAST,
        }
        ocr_strategy = strategy_map.get(strategy)
        if ocr_strategy is None:
            raise HTTPException(status_code=400, detail=f"Invalid strategy: {strategy}")

        lang_list = [l.strip() for l in languages.split(",")] if languages else None
        page_range = (page_start, page_end) if page_start and page_end else None

        # Save uploaded file to temp
        content = await file.read()
        suffix = "." + (file.filename.rsplit(".", 1)[-1] if "." in file.filename else "pdf")
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            result = await asyncio.to_thread(
                ocr_engine.process,
                tmp_path,
                strategy=ocr_strategy,
                languages=lang_list,
                page_range=page_range,
            )
            return result.to_dict()
        finally:
            os.unlink(tmp_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/ocr/status", tags=["ocr"])
async def ocr_status():
    """Get OCR engine status and available backends."""
    try:
        ocr_engine = _get_ocr_engine()
        return {
            "status": "ready",
            "initialized": ocr_engine._initialized,
            "backends": {
                "unstructured_api": ocr_engine._unstructured_available,
                "tesseract": ocr_engine._tesseract_available,
            },
            "supported_strategies": ["hi_res", "tesseract", "hybrid", "fast"],
            "supported_formats": ["pdf", "jpg", "jpeg", "png", "tiff", "bmp", "webp", "heif"],
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "not_available", "error": str(e)}


# =============================================================================
# NEO4J KNOWLEDGE GRAPH ENDPOINTS
# Property knowledge graph with Neo4j
# =============================================================================

# Lazy Neo4j instances
_neo4j_client = None
_neo4j_graph = None


def _get_neo4j_graph():
    """Get or create Neo4j graph (lazy loading)."""
    global _neo4j_client, _neo4j_graph
    if _neo4j_graph is None or not _neo4j_graph._initialized:
        try:
            from modules.graph import Neo4jClient, Neo4jConfig, PropertyKnowledgeGraph
            cfg = Neo4jConfig(
                uri=settings.neo4j_uri if hasattr(settings, "neo4j_uri") else "bolt://localhost:7687",
                user=settings.neo4j_user if hasattr(settings, "neo4j_user") else "neo4j",
                password=settings.neo4j_password if hasattr(settings, "neo4j_password") else "greenvalue_secret",
                database=settings.neo4j_database if hasattr(settings, "neo4j_database") else "neo4j",
            )
            if _neo4j_graph is None:
                _neo4j_graph = PropertyKnowledgeGraph(cfg)
            ok = _neo4j_graph.initialize(seed=True)
            if not ok:
                _neo4j_graph = None
                raise RuntimeError("PropertyKnowledgeGraph.initialize() returned False")
            _neo4j_client = _neo4j_graph.client
            logger.info("Neo4j Knowledge Graph initialized for API")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Neo4j initialization failed: {e}", exc_info=True)
            _neo4j_graph = None
            raise HTTPException(status_code=503, detail=f"Neo4j not available: {e}")
    return _neo4j_graph


@app.get("/api/v1/graph/status", tags=["graph"])
async def graph_status():
    """Get Neo4j knowledge graph status and statistics."""
    try:
        graph = _get_neo4j_graph()
        stats = graph.get_stats()
        return {"status": "connected", **stats}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "not_available", "error": str(e)}


@app.get("/api/v1/graph/context", tags=["graph"])
async def graph_context(
    query: str = Query(..., description="Query to find relevant graph context for"),
):
    """
    Get knowledge graph context for a query.
    Returns relevant property relationships, concepts, and ripple effects.
    """
    try:
        graph = _get_neo4j_graph()
        context = await asyncio.to_thread(graph.get_graph_context, query)
        return {"query": query, "graph_context": context}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Graph context failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class PropertyGraphRequest(BaseModel):
    property_id: str = Field(..., description="Property UUID")
    address: Optional[str] = Field(None, description="Property address")
    property_type: Optional[str] = Field(None, description="Type: residential, commercial, etc.")
    building_year: Optional[int] = Field(None, description="Construction year")
    energy_label: Optional[str] = Field(None, description="Energy label (A-G)")
    area_sqm: Optional[float] = Field(None, description="Property area in m2")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


@app.post("/api/v1/graph/property", tags=["graph"])
async def upsert_property(body: PropertyGraphRequest):
    """
    Upsert a property into the knowledge graph.
    Creates or updates the property node and all relationships.
    """
    try:
        graph = _get_neo4j_graph()
        result = await asyncio.to_thread(
            graph.upsert_property,
            property_id=body.property_id,
            title=body.address or body.property_id,
            address=body.address or "",
            city="",
            building_year=body.building_year or 0,
            building_type=body.property_type or "residential",
            floor_area=body.area_sqm or 0.0,
            energy_label=body.energy_label or "",
            metadata=body.metadata,
        )
        return {"status": "ok", "property_id": body.property_id, "result": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Graph property upsert failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/graph/property/{property_id}/similar", tags=["graph"])
async def find_similar_properties(
    property_id: str,
    limit: int = Query(5, ge=1, le=50, description="Max similar properties to return"),
):
    """Find properties similar to the given one in the knowledge graph."""
    try:
        graph = _get_neo4j_graph()
        results = await asyncio.to_thread(graph.find_similar_properties, property_id, limit)
        return {"property_id": property_id, "similar_properties": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Similar properties query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/graph/ripple-effects/{improvement}", tags=["graph"])
async def graph_ripple_effects(
    improvement: str,
):
    """
    Get predicted ripple effects for a property improvement.
    E.g. 'insulation_upgrade', 'solar_installation', 'window_replacement'.
    """
    try:
        graph = _get_neo4j_graph()
        effects = await asyncio.to_thread(graph.get_ripple_effects, improvement)
        return {"improvement": improvement, "effects": effects}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ripple effects query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ╔══════════════════════════════════════════════════════╗
# ║        IVS-2025 REPORT GENERATION ENDPOINTS          ║
# ╚══════════════════════════════════════════════════════╝

_report_engine = None


def _get_report_engine():
    """Lazy-load the IVS Report Engine with chain-of-thought."""
    global _report_engine
    if _report_engine is None:
        try:
            from modules.report import (
                ReportEngine,
                ChainOfThoughtEngine,
                ChartRenderer,
                PDFRenderer,
            )
            # Try to reuse the existing RAG instance if available
            rag = None
            try:
                rag = get_rag_instance()
            except Exception:
                logger.warning("RAG not available for chain-of-thought")
            chain = ChainOfThoughtEngine(
                rag_pipeline=rag,
            )
            _report_engine = ReportEngine(
                chain_engine=chain,
                chart_renderer=ChartRenderer(),
                pdf_renderer=PDFRenderer(),
            )
            logger.info("✅ IVS Report Engine loaded")
        except Exception as e:
            logger.warning(f"Report Engine not available: {e}")
            raise HTTPException(status_code=503, detail=f"Report engine unavailable: {e}")
    return _report_engine


class ReportRequest(BaseModel):
    property_id: str
    report_type: str = "full_ivs"   # full_ivs | summary | energy_only | upgrade_card
    language: str = "en"            # en | tr | de
    include_heatmap: bool = True
    include_charts: bool = True
    currency_symbol: str = "€"
    currency_code: str = "EUR"
    analysis_result: Dict = {}


@app.post("/api/v1/report/generate", tags=["report"])
async def generate_report(request: ReportRequest):
    """
    Generate an IVS-2025-compliant PDF report.
    Runs the multi-book chain-of-thought (Physics → Cost → Finance → Appraisal)
    and produces a professional PDF.
    """
    try:
        from modules.report import ReportConfig, ReportType

        engine = _get_report_engine()

        type_map = {
            "full_ivs": ReportType.FULL_IVS,
            "summary": ReportType.SUMMARY,
            "energy_only": ReportType.ENERGY_ONLY,
            "upgrade_card": ReportType.UPGRADE_CARD,
        }
        report_type = type_map.get(request.report_type, ReportType.FULL_IVS)

        config = ReportConfig(
            report_type=report_type,
            language=request.language,
            include_heatmap=request.include_heatmap,
            include_charts=request.include_charts,
            currency_symbol=request.currency_symbol,
            currency_code=request.currency_code,
        )

        result = await engine.generate(
            property_id=request.property_id,
            analysis_result=request.analysis_result,
            config=config,
        )

        response = {
            "report_id": result.report_id,
            "property_id": result.property_id,
            "report_type": result.report_type.value,
            "sections_generated": result.sections_generated,
            "ivs_compliance_warnings": result.ivs_compliance_warnings,
            "chain_of_thought_log": result.chain_of_thought_log,
            "generation_time_seconds": result.generation_time_seconds,
            "generated_at": result.generated_at,
            "has_pdf": len(result.pdf_bytes) > 0,
            "pdf_size_bytes": len(result.pdf_bytes),
        }

        if not result.pdf_bytes:
            response["metadata"] = result.metadata

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/report/generate/pdf", tags=["report"])
async def generate_report_pdf(request: ReportRequest):
    """
    Generate and directly return the IVS-2025 PDF report as a downloadable file.
    """
    from fastapi.responses import Response

    try:
        from modules.report import ReportConfig, ReportType

        engine = _get_report_engine()

        type_map = {
            "full_ivs": ReportType.FULL_IVS,
            "summary": ReportType.SUMMARY,
            "energy_only": ReportType.ENERGY_ONLY,
            "upgrade_card": ReportType.UPGRADE_CARD,
        }

        config = ReportConfig(
            report_type=type_map.get(request.report_type, ReportType.FULL_IVS),
            language=request.language,
            include_heatmap=request.include_heatmap,
            include_charts=request.include_charts,
            currency_symbol=request.currency_symbol,
            currency_code=request.currency_code,
        )

        result = await engine.generate(
            property_id=request.property_id,
            analysis_result=request.analysis_result,
            config=config,
        )

        if not result.pdf_bytes:
            raise HTTPException(
                status_code=500,
                detail="PDF generation failed — reportlab may not be installed"
            )

        return Response(
            content=result.pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="GreenValue_{result.report_id}.pdf"'
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report PDF generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/report/generate/json", tags=["report"])
async def generate_report_json(request: ReportRequest):
    """
    Generate a structured JSON report (no PDF rendering).
    Returns all IVS sections, chain-of-thought log, and compliance
    warnings in a JSON format suitable for frontend rendering.
    """
    try:
        from modules.report import ReportConfig, ReportType

        engine = _get_report_engine()

        type_map = {
            "full_ivs": ReportType.FULL_IVS,
            "summary": ReportType.SUMMARY,
            "energy_only": ReportType.ENERGY_ONLY,
            "upgrade_card": ReportType.UPGRADE_CARD,
        }
        report_type = type_map.get(request.report_type, ReportType.FULL_IVS)

        config = ReportConfig(
            report_type=report_type,
            language=request.language,
            include_heatmap=request.include_heatmap,
            include_charts=request.include_charts,
            currency_symbol=request.currency_symbol,
            currency_code=request.currency_code,
        )

        json_report = await engine.generate_json(
            property_id=request.property_id,
            analysis_result=request.analysis_result,
            config=config,
        )

        return json_report

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JSON report generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/report/ivs-sections", tags=["report"])
async def get_ivs_sections(language: str = "en"):
    """Return the IVS-2025 report section structure with localised titles."""
    from modules.report import IVSTemplate, IVSSection
    sections = []
    for section in IVSTemplate.get_ordered_sections():
        sections.append({
            "section_id": section.value,
            "title": IVSTemplate.get_section_title(section, language),
            "is_appendix": section.value.startswith("appendix_"),
        })
    return {"language": language, "sections": sections}


@app.get("/api/v1/report/books", tags=["report"])
async def get_book_library():
    """Return the RAG Knowledge Library (8-book expert mapping)."""
    from modules.rag.router import BOOK_LIBRARY
    books = []
    for key, book in BOOK_LIBRARY.items():
        books.append({
            "key": key,
            "book_id": book["book_id"],
            "title": book["title"],
            "domains": [d.value for d in book["domains"]],
            "authority": book["authority"],
            "expertise": book["expertise"],
            "chain_role": book["chain_role"],
            "chain_order": book["chain_order"],
        })
    return {"total_books": len(books), "books": books}
