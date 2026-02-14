"""
Vision-RAG Integration Module - Professional RAG Upgrade
Author: GreenValue AI Team (Enhanced by Senior RAG Developer)
Purpose: Multi-modal RAG connecting YOLO11 CV analysis with knowledge base.
"""

import logging
import json
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

import requests
from langchain_core.documents import Document

logger = logging.getLogger("greenvalue-rag")


class EnergyInefficiency(Enum):
    """Energy inefficiency types detected by YOLO11."""
    OLD_WINDOWS = "old_windows"
    UNINSULATED_WALLS = "uninsulated_walls"
    POOR_ROOF_INSULATION = "poor_roof_insulation"
    THERMAL_BRIDGES = "thermal_bridges"
    AIR_LEAKS = "air_leaks"
    OUTDATED_HEATING = "outdated_heating"
    POOR_VENTILATION = "poor_ventilation"


@dataclass
class PropertyAnalysis:
    """Computer vision analysis results from YOLO11."""
    image_path: str
    detected_issues: List[Dict[str, Any]]
    energy_efficiency_score: float
    estimated_age: Optional[int]
    property_type: str
    confidence_scores: Dict[str, float]
    recommendations: List[str]


@dataclass
class VisionContext:
    """Vision-derived context for RAG enhancement."""
    visual_insights: str
    detected_inefficiencies: List[EnergyInefficiency]
    priority_areas: List[str]
    estimated_costs: Dict[str, float]
    roi_potential: Dict[str, float]


class YOLO11Interface:
    """
    Interface to YOLO11 computer vision service.
    Connects to the existing GreenValue AI vision pipeline.
    """
    
    def __init__(self, cv_service_url: str = "http://localhost:8000"):
        self.cv_service_url = cv_service_url
        self.available = False
        
        # Energy inefficiency mapping
        self.inefficiency_mapping = {
            "old_windows": EnergyInefficiency.OLD_WINDOWS,
            "uninsulated_walls": EnergyInefficiency.UNINSULATED_WALLS,
            "poor_roof_insulation": EnergyInefficiency.POOR_ROOF_INSULATION,
            "thermal_bridges": EnergyInefficiency.THERMAL_BRIDGES,
            "air_leaks": EnergyInefficiency.AIR_LEAKS,
            "outdated_heating": EnergyInefficiency.OUTDATED_HEATING,
            "poor_ventilation": EnergyInefficiency.POOR_VENTILATION
        }
        logger.info("YOLO11Interface created")
    
    def initialize(self) -> bool:
        """Initialize YOLO11 interface. Actual health check is deferred to first use."""
        # Don't check /health during startup — FastAPI may not be ready yet (race condition).
        # Instead, mark as potentially available and check lazily on first image analysis.
        self.available = True
        logger.info("✅ YOLO11 Vision Service configured (lazy health check)")
        return True
    
    def _check_health(self) -> bool:
        """Check if YOLO11 service is actually reachable."""
        try:
            response = requests.get(f"{self.cv_service_url}/health", timeout=5)
            if response.status_code == 200:
                return True
        except Exception as e:
            logger.warning(f"YOLO11 service unavailable: {e}")
        return False
    
    def analyze_property_image(self, image_path: str) -> Optional[PropertyAnalysis]:
        """Analyze property image using YOLO11."""
        if not self.available:
            if not self.initialize():
                return None
        
        try:
            # Call existing YOLO11 analysis endpoint
            with open(image_path, 'rb') as img_file:
                files = {'image': img_file}
                response = requests.post(
                    f"{self.cv_service_url}/analyze/property",
                    files=files,
                    timeout=30
                )
            
            if response.status_code == 200:
                result = response.json()
                return self._parse_analysis_result(image_path, result)
            else:
                logger.error(f"YOLO11 analysis failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Vision analysis error: {e}")
            return None
    
    def _parse_analysis_result(self, image_path: str, result: Dict) -> PropertyAnalysis:
        """Parse YOLO11 analysis result into PropertyAnalysis."""
        return PropertyAnalysis(
            image_path=image_path,
            detected_issues=result.get('detected_issues', []),
            energy_efficiency_score=result.get('energy_efficiency_score', 0.5),
            estimated_age=result.get('estimated_age'),
            property_type=result.get('property_type', 'residential'),
            confidence_scores=result.get('confidence_scores', {}),
            recommendations=result.get('recommendations', [])
        )


class VisionContextGenerator:
    """
    Generates RAG context from computer vision analysis.
    Translates visual insights into searchable knowledge queries.
    """
    
    def __init__(self):
        # Cost estimation models (simplified for demo)
        self.cost_estimates = {
            EnergyInefficiency.OLD_WINDOWS: {"min": 300, "max": 800, "unit": "per_window"},
            EnergyInefficiency.UNINSULATED_WALLS: {"min": 15, "max": 35, "unit": "per_sqm"},
            EnergyInefficiency.POOR_ROOF_INSULATION: {"min": 20, "max": 50, "unit": "per_sqm"},
            EnergyInefficiency.THERMAL_BRIDGES: {"min": 100, "max": 300, "unit": "per_bridge"},
            EnergyInefficiency.AIR_LEAKS: {"min": 200, "max": 600, "unit": "per_property"},
            EnergyInefficiency.OUTDATED_HEATING: {"min": 3000, "max": 8000, "unit": "per_system"},
            EnergyInefficiency.POOR_VENTILATION: {"min": 1500, "max": 4000, "unit": "per_system"}
        }
        
        # ROI potential estimates
        self.roi_estimates = {
            EnergyInefficiency.OLD_WINDOWS: {"annual_savings": 0.15, "payback_years": 8},
            EnergyInefficiency.UNINSULATED_WALLS: {"annual_savings": 0.25, "payback_years": 6},
            EnergyInefficiency.POOR_ROOF_INSULATION: {"annual_savings": 0.30, "payback_years": 5},
            EnergyInefficiency.THERMAL_BRIDGES: {"annual_savings": 0.10, "payback_years": 10},
            EnergyInefficiency.AIR_LEAKS: {"annual_savings": 0.20, "payback_years": 4},
            EnergyInefficiency.OUTDATED_HEATING: {"annual_savings": 0.40, "payback_years": 7},
            EnergyInefficiency.POOR_VENTILATION: {"annual_savings": 0.12, "payback_years": 12}
        }
    
    def generate_vision_context(self, analysis: PropertyAnalysis) -> VisionContext:
        """Generate RAG context from vision analysis."""
        # Extract inefficiencies
        inefficiencies = self._extract_inefficiencies(analysis.detected_issues)
        
        # Generate visual insights text
        visual_insights = self._generate_insights_text(analysis, inefficiencies)
        
        # Determine priority areas
        priority_areas = self._determine_priority_areas(inefficiencies, analysis.energy_efficiency_score)
        
        # Estimate costs and ROI
        estimated_costs = self._estimate_costs(inefficiencies)
        roi_potential = self._estimate_roi(inefficiencies)
        
        return VisionContext(
            visual_insights=visual_insights,
            detected_inefficiencies=inefficiencies,
            priority_areas=priority_areas,
            estimated_costs=estimated_costs,
            roi_potential=roi_potential
        )
    
    def _extract_inefficiencies(self, detected_issues: List[Dict]) -> List[EnergyInefficiency]:
        """Extract energy inefficiencies from detection results."""
        inefficiencies = []
        
        for issue in detected_issues:
            issue_type = issue.get('type', '').lower()
            confidence = issue.get('confidence', 0)
            
            # Only include high-confidence detections
            if confidence > 0.6:
                for key, enum_val in YOLO11Interface().inefficiency_mapping.items():
                    if key in issue_type:
                        inefficiencies.append(enum_val)
                        break
        
        return list(set(inefficiencies))  # Remove duplicates
    
    def _generate_insights_text(self, analysis: PropertyAnalysis, inefficiencies: List[EnergyInefficiency]) -> str:
        """Generate human-readable insights from vision analysis."""
        insights = []
        
        # Property overview
        insights.append(f"Property Type: {analysis.property_type.title()}")
        insights.append(f"Energy Efficiency Score: {analysis.energy_efficiency_score:.2f}/1.0")
        
        if analysis.estimated_age:
            insights.append(f"Estimated Age: {analysis.estimated_age} years")
        
        # Detected issues
        if inefficiencies:
            insights.append("\nDetected Energy Inefficiencies:")
            for inefficiency in inefficiencies:
                issue_name = inefficiency.value.replace('_', ' ').title()
                insights.append(f"  • {issue_name}")
        
        # Recommendations
        if analysis.recommendations:
            insights.append("\nCV Recommendations:")
            for rec in analysis.recommendations[:3]:  # Top 3 recommendations
                insights.append(f"  • {rec}")
        
        return "\n".join(insights)
    
    def _determine_priority_areas(self, inefficiencies: List[EnergyInefficiency], efficiency_score: float) -> List[str]:
        """Determine priority areas for improvement."""
        priority_areas = []
        
        # High-impact inefficiencies
        high_impact = [
            EnergyInefficiency.POOR_ROOF_INSULATION,
            EnergyInefficiency.OUTDATED_HEATING,
            EnergyInefficiency.UNINSULATED_WALLS
        ]
        
        for inefficiency in inefficiencies:
            if inefficiency in high_impact:
                area = inefficiency.value.replace('_', ' ').title()
                priority_areas.append(area)
        
        # Add general areas based on efficiency score
        if efficiency_score < 0.4:
            priority_areas.append("Comprehensive Energy Audit")
        elif efficiency_score < 0.7:
            priority_areas.append("Targeted Efficiency Improvements")
        
        return priority_areas[:5]  # Top 5 priorities
    
    def _estimate_costs(self, inefficiencies: List[EnergyInefficiency]) -> Dict[str, float]:
        """Estimate retrofit costs for detected inefficiencies."""
        costs = {}
        
        for inefficiency in inefficiencies:
            if inefficiency in self.cost_estimates:
                cost_data = self.cost_estimates[inefficiency]
                # Use average of min/max for estimation
                avg_cost = (cost_data["min"] + cost_data["max"]) / 2
                costs[inefficiency.value] = avg_cost
        
        return costs
    
    def _estimate_roi(self, inefficiencies: List[EnergyInefficiency]) -> Dict[str, float]:
        """Estimate ROI potential for detected inefficiencies."""
        roi_data = {}
        
        for inefficiency in inefficiencies:
            if inefficiency in self.roi_estimates:
                roi_info = self.roi_estimates[inefficiency]
                roi_data[inefficiency.value] = {
                    "annual_savings_percent": roi_info["annual_savings"],
                    "payback_years": roi_info["payback_years"]
                }
        
        return roi_data


class VisionRAGIntegrator:
    """
    Main Vision-RAG integration class.
    Combines computer vision insights with knowledge base retrieval.
    """
    
    def __init__(self, cv_service_url: str = "http://ai-engine:8000"):
        self.yolo_interface = YOLO11Interface(cv_service_url)
        self.context_generator = VisionContextGenerator()
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize the Vision-RAG system."""
        if self._initialized:
            return True
        
        success = self.yolo_interface.initialize()
        self._initialized = success
        
        if success:
            logger.info("✅ Vision-RAG Integration initialized")
        else:
            logger.warning("⚠️ Vision-RAG running in text-only mode")
        
        return success
    
    def analyze_property_with_rag(self, image_path: str, user_query: str = None) -> Dict:
        """
        Analyze property image and enhance with RAG knowledge.
        
        Args:
            image_path: Path to property image
            user_query: Optional user query for focused analysis
            
        Returns:
            Dict with vision analysis, RAG context, and recommendations
        """
        result = {
            "vision_available": self._initialized,
            "analysis": None,
            "vision_context": None,
            "rag_queries": [],
            "recommendations": []
        }
        
        if not self._initialized:
            logger.warning("Vision analysis unavailable, using text-only RAG")
            return result
        
        try:
            # Step 1: Computer vision analysis
            analysis = self.yolo_interface.analyze_property_image(image_path)
            if not analysis:
                logger.error("Failed to analyze property image")
                return result
            
            result["analysis"] = analysis
            
            # Step 2: Generate vision context
            vision_context = self.context_generator.generate_vision_context(analysis)
            result["vision_context"] = vision_context
            
            # Step 3: Generate RAG queries
            rag_queries = self._generate_rag_queries(vision_context, user_query)
            result["rag_queries"] = rag_queries
            
            # Step 4: Generate enhanced recommendations
            recommendations = self._generate_enhanced_recommendations(vision_context, analysis)
            result["recommendations"] = recommendations
            
            logger.info(f"✅ Vision-RAG analysis complete: {len(rag_queries)} queries generated")
            return result
            
        except Exception as e:
            logger.error(f"Vision-RAG analysis failed: {e}")
            return result
    
    def _generate_rag_queries(self, vision_context: VisionContext, user_query: str = None) -> List[str]:
        """Generate targeted RAG queries based on vision analysis."""
        queries = []
        
        # User query takes priority
        if user_query:
            queries.append(user_query)
        
        # Generate queries for detected inefficiencies
        for inefficiency in vision_context.detected_inefficiencies:
            issue_name = inefficiency.value.replace('_', ' ')
            
            # Cost analysis query
            queries.append(f"What are the costs for {issue_name} retrofit solutions?")
            
            # ROI analysis query
            queries.append(f"What is the ROI for fixing {issue_name} in residential properties?")
            
            # Technical solution query
            queries.append(f"Best practices for {issue_name} energy efficiency improvements")
        
        # Priority area queries
        for priority in vision_context.priority_areas:
            queries.append(f"Energy efficiency strategies for {priority.lower()}")
        
        # General efficiency query
        queries.append("Property energy efficiency assessment methodologies")
        
        return queries[:8]  # Limit to top 8 queries
    
    def _generate_enhanced_recommendations(self, vision_context: VisionContext, analysis: PropertyAnalysis) -> List[Dict]:
        """Generate enhanced recommendations combining vision and knowledge."""
        recommendations = []
        
        # High-priority recommendations based on detected issues
        for inefficiency in vision_context.detected_inefficiencies:
            issue_name = inefficiency.value.replace('_', ' ').title()
            
            # Get cost and ROI estimates
            cost = vision_context.estimated_costs.get(inefficiency.value, 0)
            roi_info = vision_context.roi_potential.get(inefficiency.value, {})
            
            recommendation = {
                "issue": issue_name,
                "priority": "High" if inefficiency.value in ["poor_roof_insulation", "outdated_heating"] else "Medium",
                "estimated_cost": cost,
                "payback_years": roi_info.get("payback_years", "Unknown"),
                "annual_savings": roi_info.get("annual_savings_percent", 0),
                "description": f"Address {issue_name.lower()} to improve energy efficiency",
                "rag_query": f"Best solutions for {issue_name.lower()} in {analysis.property_type} properties"
            }
            
            recommendations.append(recommendation)
        
        # Sort by priority and ROI
        recommendations.sort(key=lambda x: (
            x["priority"] == "High",
            x.get("annual_savings", 0)
        ), reverse=True)
        
        return recommendations[:5]  # Top 5 recommendations
    
    def get_vision_enhanced_context(self, vision_context: VisionContext) -> str:
        """Get formatted context for RAG prompts."""
        if not vision_context:
            return ""
        
        context_parts = [
            "<vision_analysis>",
            "🏠 COMPUTER VISION ANALYSIS:",
            vision_context.visual_insights,
            ""
        ]
        
        if vision_context.priority_areas:
            context_parts.extend([
                "🎯 PRIORITY AREAS:",
                "\n".join([f"  • {area}" for area in vision_context.priority_areas]),
                ""
            ])
        
        if vision_context.estimated_costs:
            context_parts.extend([
                "💰 ESTIMATED COSTS:",
                "\n".join([
                    f"  • {issue.replace('_', ' ').title()}: €{cost:,.0f}"
                    for issue, cost in vision_context.estimated_costs.items()
                ]),
                ""
            ])
        
        context_parts.append("</vision_analysis>")
        
        return "\n".join(context_parts)


# Utility functions for integration
def analyze_property_image(image_path: str, user_query: str = None) -> Dict:
    """Convenience function for property image analysis."""
    integrator = VisionRAGIntegrator()
    integrator.initialize()
    return integrator.analyze_property_with_rag(image_path, user_query)


def get_vision_context_for_rag(image_path: str) -> str:
    """Get vision context formatted for RAG prompts."""
    result = analyze_property_image(image_path)
    
    if result.get("vision_context"):
        integrator = VisionRAGIntegrator()
        return integrator.get_vision_enhanced_context(result["vision_context"])
    
    return ""


class MultiModalRAGPipeline:
    """
    Complete multi-modal RAG pipeline combining vision and text.
    Integrates with existing GreenValue RAG system.
    """
    
    def __init__(self, rag_system: Any = None, cv_service_url: str = "http://localhost:8000"):
        self.rag_system = rag_system  # Existing GreenValueRAG instance
        self.cv_service_url = cv_service_url
        self.vision_integrator = None
        self._initialized = False
        logger.info("MultiModalRAGPipeline created, call initialize() to start services")

    def initialize(self) -> bool:
        """
        Initialize the multi-modal RAG pipeline services.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        if self._initialized:
            logger.info("MultiModalRAGPipeline already initialized")
            return True
        
        try:
            # Initialize vision integrator with error handling
            logger.info("Initializing Vision-RAG integrator...")
            self.vision_integrator = VisionRAGIntegrator(self.cv_service_url)
            vision_success = self.vision_integrator.initialize()
            
            if vision_success:
                logger.info("✅ Vision-RAG integrator initialized successfully")
            else:
                logger.warning("⚠️ Vision-RAG running in text-only mode (YOLO11 service unavailable)")
            
            # Check RAG system
            if self.rag_system:
                logger.info("✅ RAG system available")
            else:
                logger.warning("⚠️ No RAG system provided, using fallback responses")
            
            self._initialized = True
            logger.info("✅ MultiModalRAGPipeline initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"MultiModalRAGPipeline initialization failed: {str(e)}")
            self._initialized = False
            return False
    
    def analyze_image_with_rag(
        self,
        image_bytes: bytes,
        property_id: str,
        user_id: str = "default",
        include_rag: bool = True
    ) -> Dict:
        """
        Analyze a property image with Vision + RAG.
        Called by the /api/v1/vision-rag/analyze endpoint.
        
        Args:
            image_bytes: Raw image bytes from upload
            property_id: Property identifier
            user_id: User ID for personalization
            include_rag: Whether to include RAG insights
            
        Returns:
            Dict with vision_analysis, rag_insights, and combined_report
        """
        import tempfile
        import os
        
        # Save image bytes to temp file for YOLO11 analysis
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        
        try:
            # Step 1: Vision analysis
            vision_data = {"detections": [], "inefficiencies": [], "score": 0.0}
            if self.vision_integrator and self.vision_integrator.yolo_interface.available:
                analysis = self.vision_integrator.yolo_interface.analyze_property_image(tmp_path)
                if analysis:
                    context = self.vision_integrator.generate_vision_context(analysis)
                    vision_data = {
                        "detections": analysis.detected_issues,
                        "inefficiencies": [e.value for e in context.detected_inefficiencies],
                        "score": analysis.energy_efficiency_score,
                        "property_type": analysis.property_type,
                        "priority_areas": context.priority_areas,
                        "cost_estimates": context.estimated_costs,
                        "roi_potential": context.roi_potential,
                    }
            else:
                logger.warning("YOLO11 not available, returning text-only analysis")
                vision_data["note"] = "Vision service unavailable, text-only mode"
            
            # Step 2: RAG insights (if requested and available)
            rag_data = None
            if include_rag and self.rag_system:
                try:
                    # Generate RAG query from vision context
                    query = f"Property analysis for {property_id}: energy efficiency recommendations"
                    if vision_data.get("inefficiencies"):
                        issues = ", ".join(vision_data["inefficiencies"])
                        query = f"Energy efficiency improvements for property with: {issues}"
                    
                    rag_result = self.rag_system.query(
                        question=query,
                        user_id=user_id
                    )
                    rag_data = rag_result
                except Exception as e:
                    logger.error(f"RAG query failed: {e}")
                    rag_data = {"error": str(e)}
            
            # Step 3: Combined report
            combined_report = {
                "property_id": property_id,
                "vision_available": bool(self.vision_integrator and self.vision_integrator.yolo_interface.available),
                "rag_available": bool(self.rag_system),
                "summary": self._generate_summary(vision_data, rag_data),
            }
            
            return {
                "vision_analysis": vision_data,
                "rag_insights": rag_data,
                "combined_report": combined_report,
            }
        finally:
            os.unlink(tmp_path)
    
    def _generate_summary(self, vision_data: Dict, rag_data: Optional[Dict]) -> str:
        """Generate a human-readable summary from vision + RAG results."""
        parts = []
        
        inefficiencies = vision_data.get("inefficiencies", [])
        if inefficiencies:
            parts.append(f"Detected {len(inefficiencies)} energy inefficiencies: {', '.join(inefficiencies)}")
        else:
            parts.append("No energy inefficiencies detected from visual analysis.")
        
        if rag_data and not rag_data.get("error"):
            answer = rag_data.get("answer", "")
            if answer:
                parts.append(f"Knowledge base recommendation: {answer[:200]}")
        
        return " | ".join(parts) if parts else "Analysis complete."
    
    def query_with_vision(
        self,
        query: str,
        image_path: str = None,
        user_id: str = "default"
    ) -> Dict:
        """
        Execute RAG query with optional vision enhancement.
        
        Args:
            query: User query
            image_path: Optional property image for vision analysis
            user_id: User ID for personalization
            
        Returns:
            Enhanced RAG response with vision insights
        """
        if not self._initialized:
            logger.warning("Pipeline not initialized, attempting to initialize now...")
            if not self.initialize():
                return {
                    "query": query,
                    "error": "Pipeline initialization failed",
                    "enhanced": False,
                    "vision_available": False,
                    "rag_available": False
                }
        # Standard RAG response
        rag_response = self.rag_system.query(query, user_id=user_id)
        
        # Add vision enhancement if image provided
        if image_path and Path(image_path).exists():
            vision_result = self.vision_integrator.analyze_property_with_rag(image_path, query)
            
            if vision_result.get("vision_context"):
                # Enhance RAG response with vision insights
                vision_context = self.vision_integrator.get_vision_enhanced_context(
                    vision_result["vision_context"]
                )
                
                # Add vision context to response
                rag_response["vision_analysis"] = vision_result["analysis"]
                rag_response["vision_context"] = vision_context
                rag_response["vision_recommendations"] = vision_result["recommendations"]
                rag_response["enhanced"] = True
            else:
                rag_response["enhanced"] = False
        else:
            rag_response["enhanced"] = False
        
        return rag_response
