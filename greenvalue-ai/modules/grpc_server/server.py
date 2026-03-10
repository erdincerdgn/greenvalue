# ============================================================
# GreenValue AI Engine — gRPC Server
# Implements AIService from greenvalue/v1/ai_service.proto
# ============================================================

import asyncio
import logging
import time
from concurrent import futures
from pathlib import Path
from typing import Optional

import grpc

try:
    from grpc_reflection.v1alpha import reflection
    HAS_REFLECTION = True
except ImportError:
    HAS_REFLECTION = False

from config.settings import get_settings

logger = logging.getLogger("greenvalue-ai.grpc")


class AIServiceServicer:
    """
    gRPC servicer implementing greenvalue.ai.v1.AIService.

    Bridges gRPC calls to the existing pipeline, physics engine,
    and YOLO inference modules.
    """

    def __init__(self, pipeline, inference_engine, physics_engine,
                 report_engine=None, chain_engine=None, rag_pipeline=None):
        self.pipeline = pipeline
        self.engine = inference_engine
        self.physics = physics_engine
        self.report_engine = report_engine
        self.chain_engine = chain_engine
        self.rag_pipeline = rag_pipeline
        self.settings = get_settings()
        self._start_time = time.time()
        # In-memory job status tracking (same as FastAPI app state)
        self._jobs: dict = {}

    def AnalyzeImage(self, request, context):
        """Run the full Scan-to-Value analysis pipeline."""
        import threading

        job_id = request.job_id or str(__import__("uuid").uuid4())
        logger.info(f"[gRPC] AnalyzeImage called: job_id={job_id}, property_id={request.property_id}")

        # Track the job
        self._jobs[job_id] = {
            "status": "PROCESSING",
            "progress": 0,
            "current_step": "starting",
        }

        try:
            # Run the async pipeline in a new event loop (gRPC handlers are sync)
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(
                self.pipeline.run(
                    job_id=job_id,
                    file_key=request.file_key,
                    property_id=request.property_id,
                    model_size=request.model_size or None,
                )
            )
            loop.close()

            # Update job status
            self._jobs[job_id] = {
                "status": "COMPLETED",
                "progress": 100,
                "current_step": "done",
                "result": result,
            }

            # Build response using the dynamically loaded message classes
            response = self._build_analyze_response(job_id, result)
            return response

        except Exception as e:
            logger.error(f"[gRPC] AnalyzeImage failed: {e}", exc_info=True)
            self._jobs[job_id] = {
                "status": "FAILED",
                "progress": 0,
                "current_step": "error",
                "error": str(e),
            }
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return self._response_classes["AnalyzeImageResponse"]()

    def GetAnalysisStatus(self, request, context):
        """Get the status of a running or completed analysis job."""
        job_id = request.job_id
        job = self._jobs.get(job_id)

        if not job:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Job {job_id} not found")
            return self._response_classes["GetAnalysisStatusResponse"]()

        status_map = {
            "QUEUED": 1, "PROCESSING": 2, "COMPLETED": 3, "FAILED": 4,
        }

        response = self._response_classes["GetAnalysisStatusResponse"](
            job_id=job_id,
            status=status_map.get(job["status"], 0),
            progress_percent=job.get("progress", 0),
            current_step=job.get("current_step", ""),
            error_message=job.get("error", ""),
        )

        # If completed, attach result
        if job["status"] == "COMPLETED" and "result" in job:
            result = job["result"]
            response.result.CopyFrom(self._build_analysis_result(result))

        return response

    def CalculateUValue(self, request, context):
        """Calculate U-Value for building components."""
        logger.info(f"[gRPC] CalculateUValue called: {len(request.components)} components")

        try:
            # Convert proto components to detection-like dicts for physics engine
            detections = []
            for comp in request.components:
                detections.append({
                    "class_name": comp.component_type,
                    "area_pixels": comp.area_m2 * 1000,  # reverse pixel_to_m2_ratio
                    "confidence": 0.95,
                    "bbox": {"x_min": 0, "y_min": 0, "x_max": 100, "y_max": 100},
                })

            physics_result = self.physics.analyze_components(detections)

            # Build component U-Value results
            comp_results = []
            for comp in physics_result.get("components", []):
                comp_results.append(
                    self._response_classes["ComponentUValue"](
                        component_type=comp.get("component_type", ""),
                        u_value=comp.get("u_value", 0),
                        heat_loss_percentage=comp.get("heat_loss_percentage", 0),
                        rating=comp.get("condition", "unknown"),
                    )
                )

            # Build renovation suggestion
            renovation = physics_result.get("renovation", {})
            suggestion = self._response_classes["RenovationSuggestion"](
                projected_u_value=renovation.get("projected_u_value", 0),
                projected_energy_label=renovation.get("projected_energy_label", ""),
                estimated_cost_eur=renovation.get("estimated_cost_eur", 0),
                annual_savings_eur=renovation.get("annual_savings_eur", 0),
                payback_years=renovation.get("payback_years", 0),
                roi_percentage=renovation.get("roi_percentage", 0),
                recommended_actions=renovation.get("recommended_actions", []),
            )

            return self._response_classes["CalculateUValueResponse"](
                total_u_value=physics_result.get("overall_u_value", 0),
                energy_label=physics_result.get("energy_label", ""),
                components=comp_results,
                annual_heat_loss_kwh=physics_result.get("total_annual_heat_loss_kwh", 0),
                annual_energy_cost_eur=physics_result.get("annual_energy_cost_eur", 0),
                suggestion=suggestion,
            )

        except Exception as e:
            logger.error(f"[gRPC] CalculateUValue failed: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return self._response_classes["CalculateUValueResponse"]()

    def GenerateReport(self, request, context):
        """Generate a PDF/JSON report via ReportEngine."""
        job_id = request.job_id or str(__import__("uuid").uuid4())
        logger.info(f"[gRPC] GenerateReport called: property_id={request.property_id}, job_id={job_id}")

        if not self.report_engine:
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details("ReportEngine not initialised")
            return self._response_classes["GenerateReportResponse"]()

        try:
            from modules.report.engine import ReportConfig, ReportType as EngineReportType

            # Map proto ReportType enum to engine ReportType
            report_type_map = {
                0: EngineReportType.FULL_IVS,       # UNSPECIFIED → default
                1: EngineReportType.ENERGY_ONLY,     # ENERGY_CERTIFICATE
                2: EngineReportType.FULL_IVS,        # ROI_ANALYSIS
                3: EngineReportType.FULL_IVS,        # COMPARISON
                4: EngineReportType.FULL_IVS,        # FULL_IVS
            }
            engine_type = report_type_map.get(request.report_type, EngineReportType.FULL_IVS)
            config = ReportConfig(report_type=engine_type)

            # Retrieve analysis result from job store (if available)
            analysis_result = {}
            if job_id in self._jobs and "result" in self._jobs[job_id]:
                analysis_result = self._jobs[job_id]["result"]
            else:
                analysis_result = {"property_id": request.property_id}

            # Run async report generation in a new loop
            loop = asyncio.new_event_loop()
            report_result = loop.run_until_complete(
                self.report_engine.generate(
                    property_id=request.property_id,
                    analysis_result=analysis_result,
                    config=config,
                )
            )
            loop.close()

            # Upload PDF to MinIO/RustFS if storage available
            report_key = ""
            report_url = ""
            if report_result.pdf_bytes:
                try:
                    from modules.storage.minio_client import get_storage_service
                    storage = get_storage_service()
                    if not storage.client:
                        storage.connect()
                    client = storage.client
                    report_key = f"pdf-reports/{request.property_id}/{report_result.report_id}.pdf"
                    import io
                    client.put_object(
                        self.settings.MINIO_BUCKET_REPORTS
                        if hasattr(self.settings, "MINIO_BUCKET_REPORTS")
                        else "pdf-reports",
                        report_key,
                        io.BytesIO(report_result.pdf_bytes),
                        len(report_result.pdf_bytes),
                        content_type="application/pdf",
                    )
                    logger.info(f"[gRPC] Report uploaded: {report_key}")
                except Exception as upload_err:
                    logger.warning(f"[gRPC] Report storage upload failed: {upload_err}")
                    report_key = f"local://{report_result.report_id}.pdf"

            return self._response_classes["GenerateReportResponse"](
                report_key=report_key,
                report_url=report_url,
                report_type=request.report_type,
            )

        except Exception as e:
            logger.error(f"[gRPC] GenerateReport failed: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return self._response_classes["GenerateReportResponse"]()

    def FindSimilarProperties(self, request, context):
        """Find visually similar properties via Qdrant vector similarity."""
        logger.info(f"[gRPC] FindSimilarProperties called: property_id={request.property_id}")

        if not self.rag_pipeline:
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details("RAG pipeline not initialised")
            return self._response_classes["FindSimilarResponse"]()

        try:
            limit = request.limit if request.limit > 0 else 10
            filter_labels = list(request.filter_labels) if request.filter_labels else None

            # Build query from property context
            query = f"Property {request.property_id} building characteristics energy efficiency"
            if request.image_key:
                query += f" visual features from {request.image_key}"

            # Retrieve similar documents from Qdrant
            loop = asyncio.new_event_loop()
            docs = loop.run_until_complete(
                self._async_similarity_search(query, limit, filter_labels)
            )
            loop.close()

            # Convert documents to SimilarProperty messages
            properties = []
            seen_ids = set()
            for doc in docs:
                prop_id = doc.metadata.get("property_id", doc.metadata.get("source", ""))
                if prop_id in seen_ids:
                    continue
                seen_ids.add(prop_id)

                properties.append(
                    self._response_classes["SimilarProperty"](
                        property_id=prop_id,
                        similarity_score=doc.metadata.get("score", 0.0),
                        energy_label=doc.metadata.get("energy_label", ""),
                        thumbnail_url=doc.metadata.get("thumbnail_url", ""),
                    )
                )

            return self._response_classes["FindSimilarResponse"](properties=properties)

        except Exception as e:
            logger.error(f"[gRPC] FindSimilarProperties failed: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return self._response_classes["FindSimilarResponse"]()

    async def _async_similarity_search(self, query: str, limit: int, filter_labels=None):
        """Helper: run similarity search through RAG pipeline."""
        try:
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.rag_pipeline._enhanced_retrieval.similarity_search(
                    query, top_k=limit
                )
            )
            # Apply energy label filter if provided
            if filter_labels:
                results = [
                    d for d in results
                    if d.metadata.get("energy_label", "") in filter_labels
                ]
            return results
        except Exception:
            # Fallback: use retrieve method
            return self.rag_pipeline._enhanced_retrieval.retrieve(query, top_k=limit)

    def GetPropertyGraph(self, request, context):
        """Get property knowledge graph relationships and ripple effects."""
        logger.info(f"[gRPC] GetPropertyGraph called: property_id={request.property_id}, query={request.query}")

        try:
            from modules.rag.graph import KnowledgeGraph, PropertyGraph

            relations = []
            ripple_effects = []
            related_factors = []
            summary_parts = []

            # 1. Get knowledge graph context from query
            if request.query:
                graph_ctx = KnowledgeGraph.get_graph_context(request.query)
                if graph_ctx:
                    summary_parts.append(graph_ctx)

                # Extract matching relations
                q = request.query.lower()
                for (src, rel, tgt), conf in KnowledgeGraph.RELATIONS.items():
                    matched = False
                    for kw, concept in KnowledgeGraph.CONCEPT_MAPPING.items():
                        if kw in q and (concept == src or concept == tgt):
                            matched = True
                            break
                    if matched:
                        relations.append(
                            self._response_classes["GraphRelation"](
                                source=src.replace("_", " ").title(),
                                relation=rel,
                                target=tgt.replace("_", " ").title(),
                                confidence=conf,
                            )
                        )

            # 2. Get ripple effects for requested improvements
            prop_graph = PropertyGraph()
            improvement_types = list(request.improvement_types) if request.improvement_types else []

            # If no improvements specified, use all available
            if not improvement_types:
                improvement_types = list(PropertyGraph.RIPPLE_EFFECTS.keys())

            for imp in improvement_types:
                effects = PropertyGraph.RIPPLE_EFFECTS.get(imp, {})
                for factor, change in effects.items():
                    ripple_effects.append(
                        self._response_classes["RippleEffect"](
                            improvement=imp.replace("_", " ").title(),
                            factor=factor.replace("_", " ").title(),
                            change_percent=change * 100,  # Convert to percentage
                        )
                    )

                ripple_text = prop_graph.get_ripple_effects(imp)
                if ripple_text:
                    summary_parts.append(ripple_text)

            # 3. Get related factors for known components
            for comp_key, factors in PropertyGraph.FACTOR_RELATIONS.items():
                for f in factors:
                    if f not in related_factors:
                        related_factors.append(f.replace("_", " ").title())

            return self._response_classes["GetPropertyGraphResponse"](
                relations=relations,
                ripple_effects=ripple_effects,
                related_factors=related_factors,
                summary="\n".join(summary_parts) if summary_parts else "No graph context available.",
            )

        except Exception as e:
            logger.error(f"[gRPC] GetPropertyGraph failed: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return self._response_classes["GetPropertyGraphResponse"]()

    def ChainOfThoughtAnalysis(self, request, context):
        """Run chain-of-thought multi-book analysis for renovation recommendations."""
        logger.info(f"[gRPC] ChainOfThoughtAnalysis called: property_id={request.property_id}")

        if not self.chain_engine:
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details("ChainOfThoughtEngine not initialised")
            return self._response_classes["ChainOfThoughtResponse"]()

        try:
            # Convert proto detections to dicts
            detections = [
                {
                    "class_name": d.class_name,
                    "confidence": d.confidence,
                    "area_m2": d.area_m2,
                    "condition": d.condition,
                    "u_value": d.u_value,
                }
                for d in request.detections
            ]

            # Convert proto u_values to dicts
            u_values = [
                {
                    "component_type": u.component_type,
                    "u_value": u.u_value,
                    "area_m2": u.area_m2,
                    "heat_loss_kwh": u.heat_loss_kwh,
                }
                for u in request.u_values
            ]

            # Property metadata from proto map
            property_meta = dict(request.property_meta) if request.property_meta else {}

            # Run async chain-of-thought
            loop = asyncio.new_event_loop()
            chain_result = loop.run_until_complete(
                self.chain_engine.execute(
                    detections=detections,
                    u_values=u_values,
                    energy_label=request.energy_label,
                    property_meta=property_meta,
                )
            )
            loop.close()

            # Build upgrade recommendations
            upgrades = []
            for u in chain_result.upgrades:
                upgrades.append(
                    self._response_classes["UpgradeRecommendation"](
                        component=u.get("component", ""),
                        action=u.get("action", ""),
                        cost=u.get("cost", 0),
                        value_add=u.get("value_add", 0),
                        roi_percent=u.get("roi_percent", 0),
                        payback_years=u.get("payback_years", 0),
                        energy_savings_kwh=u.get("energy_savings_kwh", 0),
                        co2_reduction_kg=u.get("co2_reduction_kg", 0),
                        book_source=u.get("book_source", ""),
                    )
                )

            # Build step logs
            step_logs = []
            for log in chain_result.step_logs:
                step_logs.append(
                    self._response_classes["StepLog"](
                        step_name=log.get("step_name", ""),
                        book_id=log.get("book_id", ""),
                        query_used=log.get("query_used", ""),
                        chunks_retrieved=log.get("chunks_retrieved", 0),
                        duration_seconds=log.get("duration_seconds", 0),
                        summary=log.get("summary", ""),
                    )
                )

            return self._response_classes["ChainOfThoughtResponse"](
                success=chain_result.success,
                upgrades=upgrades,
                total_cost=chain_result.total_cost,
                total_value_add=chain_result.total_value_add,
                aggregate_roi=chain_result.aggregate_roi,
                label_before=chain_result.label_before,
                label_after=getattr(chain_result, "label_after", ""),
                step_logs=step_logs,
                duration_seconds=chain_result.total_duration_seconds,
                error=chain_result.error or "",
            )

        except Exception as e:
            logger.error(f"[gRPC] ChainOfThoughtAnalysis failed: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return self._response_classes["ChainOfThoughtResponse"]()

    def HealthCheck(self, request, context):
        """Return health and GPU status."""
        uptime = time.time() - self._start_time

        gpu_available = False
        gpu_name = ""
        gpu_memory_mb = 0

        try:
            import torch
            if torch.cuda.is_available():
                gpu_available = True
                gpu_name = torch.cuda.get_device_name(0)
                props = torch.cuda.get_device_properties(0)
                gpu_memory_mb = getattr(props, 'total_memory', getattr(props, 'total_mem', 0)) // (1024 * 1024)
        except ImportError:
            pass

        return self._response_classes["HealthCheckResponse"](
            status="healthy" if self.engine.is_loaded else "degraded",
            gpu_available=gpu_available,
            gpu_name=gpu_name,
            gpu_memory_mb=gpu_memory_mb,
            model_loaded=self.engine.model_version or "none",
            uptime_seconds=uptime,
        )

    # ── Helpers ──────────────────────────────────────────────

    def set_response_classes(self, classes: dict):
        """Store dynamically loaded proto message classes."""
        self._response_classes = classes

    def _build_analyze_response(self, job_id: str, result: dict):
        """Build AnalyzeImageResponse from pipeline result."""
        analysis_result = self._build_analysis_result(result)

        return self._response_classes["AnalyzeImageResponse"](
            job_id=job_id,
            status=3,  # COMPLETED
            result=analysis_result,
            error_message="",
        )

    def _build_analysis_result(self, result: dict):
        """Build AnalysisResult proto from pipeline result dict."""
        inference = result.get("inference", {})
        physics = result.get("physics", {})
        artifacts = result.get("artifacts", {})
        img_meta = result.get("image_metadata", {})

        # Build detections
        detections = []
        for det in inference.get("detections", []):
            bbox = det.get("bbox", {})
            detection = self._response_classes["Detection"](
                class_name=det.get("class_name", ""),
                confidence=det.get("confidence", 0),
                bbox=self._response_classes["BoundingBox"](
                    x_min=bbox.get("x_min", 0),
                    y_min=bbox.get("y_min", 0),
                    x_max=bbox.get("x_max", 0),
                    y_max=bbox.get("y_max", 0),
                ),
                area_m2=det.get("area_pixels", 0) * 0.001,
                u_value=det.get("u_value", 0),
            )
            if det.get("mask_polygon"):
                detection.mask_polygon.extend(det["mask_polygon"])
            detections.append(detection)

        # Build image metadata
        image_metadata = self._response_classes["ImageMetadata"](
            width=img_meta.get("width", 0),
            height=img_meta.get("height", 0),
            format=img_meta.get("format", ""),
        )

        return self._response_classes["AnalysisResult"](
            detections=detections,
            overall_u_value=physics.get("overall_u_value", 0),
            energy_label=physics.get("energy_label", ""),
            heatmap_key=artifacts.get("heatmap_key", ""),
            confidence_score=sum(d.get("confidence", 0) for d in inference.get("detections", [])) / max(len(inference.get("detections", [])), 1),
            model_version=inference.get("model_version", ""),
            inference_time_ms=inference.get("inference_time_ms", 0),
            image_metadata=image_metadata,
        )


def create_grpc_server(pipeline, inference_engine, physics_engine, port: int = 50051,
                       report_engine=None, chain_engine=None, rag_pipeline=None):
    """
    Create and configure the gRPC server with AIService.

    Uses dynamic proto loading (same approach as the NestJS backend)
    to avoid needing pre-generated Python stubs.
    """
    from grpc_tools import protoc
    import importlib
    import sys
    import tempfile
    import os

    settings = get_settings()
    # __file__ is at: /app/modules/grpc_server/server.py
    # App root is at: /app/
    app_root = Path(__file__).parent.parent.parent
    proto_dir = app_root / "protos"
    proto_file = "greenvalue/v1/ai_service.proto"

    # Generate stubs to a temp directory
    out_dir = Path(__file__).parent / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "__init__.py").touch()
    # Create package dirs for generated code
    gv_dir = out_dir / "greenvalue"
    gv_dir.mkdir(exist_ok=True)
    (gv_dir / "__init__.py").touch()
    v1_dir = gv_dir / "v1"
    v1_dir.mkdir(exist_ok=True)
    (v1_dir / "__init__.py").touch()

    # Run protoc
    protoc_args = [
        "",  # first arg is ignored by protoc
        f"--proto_path={proto_dir}",
        f"--python_out={out_dir}",
        f"--grpc_python_out={out_dir}",
        proto_file,
    ]

    logger.info(f"Generating gRPC stubs from {proto_dir / proto_file}")
    result = protoc.main(protoc_args)
    if result != 0:
        raise RuntimeError(f"protoc failed with code {result}")

    # Fix the import in generated grpc file (protoc generates absolute imports)
    grpc_file = out_dir / "greenvalue" / "v1" / "ai_service_pb2_grpc.py"
    if grpc_file.exists():
        content = grpc_file.read_text()
        content = content.replace(
            "from greenvalue.v1 import ai_service_pb2",
            "from . import ai_service_pb2"
        )
        grpc_file.write_text(content)

    # Add to sys.path and import
    if str(out_dir) not in sys.path:
        sys.path.insert(0, str(out_dir))

    from greenvalue.v1 import ai_service_pb2
    from greenvalue.v1 import ai_service_pb2_grpc

    # Create servicer
    servicer = AIServiceServicer(
        pipeline, inference_engine, physics_engine,
        report_engine=report_engine,
        chain_engine=chain_engine,
        rag_pipeline=rag_pipeline,
    )

    # Provide response message classes to the servicer
    servicer.set_response_classes({
        "AnalyzeImageResponse": ai_service_pb2.AnalyzeImageResponse,
        "AnalysisResult": ai_service_pb2.AnalysisResult,
        "Detection": ai_service_pb2.Detection,
        "BoundingBox": ai_service_pb2.BoundingBox,
        "ImageMetadata": ai_service_pb2.ImageMetadata,
        "GetAnalysisStatusResponse": ai_service_pb2.GetAnalysisStatusResponse,
        "CalculateUValueResponse": ai_service_pb2.CalculateUValueResponse,
        "ComponentUValue": ai_service_pb2.ComponentUValue,
        "RenovationSuggestion": ai_service_pb2.RenovationSuggestion,
        "GenerateReportResponse": ai_service_pb2.GenerateReportResponse,
        "FindSimilarResponse": ai_service_pb2.FindSimilarResponse,
        "SimilarProperty": ai_service_pb2.SimilarProperty,
        "HealthCheckResponse": ai_service_pb2.HealthCheckResponse,
        # New: Property Graph
        "GetPropertyGraphResponse": ai_service_pb2.GetPropertyGraphResponse,
        "GraphRelation": ai_service_pb2.GraphRelation,
        "RippleEffect": ai_service_pb2.RippleEffect,
        # New: Chain-of-Thought
        "ChainOfThoughtResponse": ai_service_pb2.ChainOfThoughtResponse,
        "UpgradeRecommendation": ai_service_pb2.UpgradeRecommendation,
        "StepLog": ai_service_pb2.StepLog,
    })

    # Create gRPC server
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=4),
        options=[
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.keepalive_time_ms", 15000),
            ("grpc.keepalive_timeout_ms", 5000),
        ],
    )

    # Register servicer
    ai_service_pb2_grpc.add_AIServiceServicer_to_server(servicer, server)

    # Enable server reflection if available (for debugging with grpcurl)
    if HAS_REFLECTION:
        service_names = (
            ai_service_pb2.DESCRIPTOR.services_by_name["AIService"].full_name,
            reflection.SERVICE_NAME,
        )
        reflection.enable_server_reflection(service_names, server)
        logger.info("gRPC server reflection enabled")

    # Bind port
    listen_addr = f"0.0.0.0:{port}"
    server.add_insecure_port(listen_addr)

    logger.info(f"gRPC server configured on {listen_addr}")
    return server
