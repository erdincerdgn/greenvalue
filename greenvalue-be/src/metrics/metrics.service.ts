import { Injectable, OnModuleInit } from '@nestjs/common';
import { OnEvent } from '@nestjs/event-emitter';
import * as client from 'prom-client';

/**
 * Metrics Service for GreenValue AI Platform
 *
 * Prometheus metrics:
 * - HTTP request metrics
 * - Analysis metrics (image analysis, U-value calculations)
 * - Report generation metrics
 * - AI Engine health & performance
 * - System metrics (WebSocket, Redis)
 */
@Injectable()
export class MetricsService implements OnModuleInit {
    private registry: client.Registry;

    // HTTP Metrics
    public httpRequestsTotal: client.Counter<string>;
    public httpRequestDuration: client.Histogram<string>;

    // Analysis Metrics
    public analysesTotal: client.Counter<string>;
    public analysisLatency: client.Histogram<string>;
    public analysesInProgress: client.Gauge<string>;

    // U-Value Metrics
    public uValueCalculations: client.Counter<string>;

    // Report Metrics
    public reportsGenerated: client.Counter<string>;
    public reportLatency: client.Histogram<string>;

    // AI Engine Metrics
    public detectionConfidence: client.Histogram<string>;
    public aiEngineStatus: client.Gauge<string>;

    // System Metrics
    public websocketConnections: client.Gauge<string>;
    public redisLatency: client.Histogram<string>;

    constructor() {
        this.registry = new client.Registry();
        client.collectDefaultMetrics({ register: this.registry });
        this.initializeMetrics();
    }

    onModuleInit() {
        // Metrics are already initialized in constructor
    }

    private initializeMetrics(): void {
        // ==========================================
        // HTTP METRICS
        // ==========================================

        this.httpRequestsTotal = new client.Counter({
            name: 'greenvalue_http_requests_total',
            help: 'Total number of HTTP requests',
            labelNames: ['method', 'path', 'status'],
            registers: [this.registry],
        });

        this.httpRequestDuration = new client.Histogram({
            name: 'greenvalue_http_request_duration_seconds',
            help: 'HTTP request duration in seconds',
            labelNames: ['method', 'path', 'status'],
            buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5],
            registers: [this.registry],
        });

        // ==========================================
        // ANALYSIS METRICS
        // ==========================================

        this.analysesTotal = new client.Counter({
            name: 'greenvalue_analyses_total',
            help: 'Total number of analyses submitted',
            labelNames: ['status', 'building_type'],
            registers: [this.registry],
        });

        this.analysisLatency = new client.Histogram({
            name: 'greenvalue_analysis_duration_seconds',
            help: 'Analysis processing duration in seconds',
            labelNames: ['building_type'],
            buckets: [1, 5, 10, 30, 60, 120, 300],
            registers: [this.registry],
        });

        this.analysesInProgress = new client.Gauge({
            name: 'greenvalue_analyses_in_progress',
            help: 'Number of analyses currently being processed',
            registers: [this.registry],
        });

        // ==========================================
        // U-VALUE METRICS
        // ==========================================

        this.uValueCalculations = new client.Counter({
            name: 'greenvalue_u_value_calculations_total',
            help: 'Total U-Value calculations performed',
            labelNames: ['component'],
            registers: [this.registry],
        });

        // ==========================================
        // REPORT METRICS
        // ==========================================

        this.reportsGenerated = new client.Counter({
            name: 'greenvalue_reports_generated_total',
            help: 'Total reports generated',
            labelNames: ['format'],
            registers: [this.registry],
        });

        this.reportLatency = new client.Histogram({
            name: 'greenvalue_report_generation_seconds',
            help: 'Report generation duration in seconds',
            labelNames: ['format'],
            buckets: [1, 5, 10, 30, 60],
            registers: [this.registry],
        });

        // ==========================================
        // AI ENGINE METRICS
        // ==========================================

        this.detectionConfidence = new client.Histogram({
            name: 'greenvalue_detection_confidence',
            help: 'Detection confidence scores from AI engine',
            labelNames: ['class_name'],
            buckets: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registers: [this.registry],
        });

        this.aiEngineStatus = new client.Gauge({
            name: 'greenvalue_ai_engine_status',
            help: 'AI Engine status (0=down, 1=healthy)',
            registers: [this.registry],
        });

        // ==========================================
        // SYSTEM METRICS
        // ==========================================

        this.websocketConnections = new client.Gauge({
            name: 'greenvalue_websocket_connections',
            help: 'Number of active WebSocket connections',
            registers: [this.registry],
        });

        this.redisLatency = new client.Histogram({
            name: 'greenvalue_redis_latency_seconds',
            help: 'Redis operation latency',
            labelNames: ['operation'],
            buckets: [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1],
            registers: [this.registry],
        });
    }

    // ==========================================
    // METRICS ENDPOINT
    // ==========================================

    async getMetrics(): Promise<string> {
        return this.registry.metrics();
    }

    getContentType(): string {
        return this.registry.contentType;
    }

    // ==========================================
    // EVENT HANDLERS
    // ==========================================

    @OnEvent('analysis.started')
    handleAnalysisStarted(payload: { buildingType?: string }): void {
        this.analysesTotal.inc({
            status: 'started',
            building_type: payload.buildingType || 'unknown',
        });
        this.analysesInProgress.inc();
    }

    @OnEvent('analysis.completed')
    handleAnalysisCompleted(payload: {
        buildingType?: string;
        durationMs?: number;
    }): void {
        this.analysesTotal.inc({
            status: 'completed',
            building_type: payload.buildingType || 'unknown',
        });
        this.analysesInProgress.dec();

        if (payload.durationMs) {
            this.analysisLatency.observe(
                { building_type: payload.buildingType || 'unknown' },
                payload.durationMs / 1000,
            );
        }
    }

    @OnEvent('analysis.failed')
    handleAnalysisFailed(payload: { buildingType?: string }): void {
        this.analysesTotal.inc({
            status: 'failed',
            building_type: payload.buildingType || 'unknown',
        });
        this.analysesInProgress.dec();
    }

    @OnEvent('uvalue.calculated')
    handleUValueCalculated(payload: { component?: string }): void {
        this.uValueCalculations.inc({
            component: payload.component || 'composite',
        });
    }

    @OnEvent('report.generated')
    handleReportGenerated(payload: { format: string; durationMs?: number }): void {
        this.reportsGenerated.inc({ format: payload.format });
        if (payload.durationMs) {
            this.reportLatency.observe(
                { format: payload.format },
                payload.durationMs / 1000,
            );
        }
    }

    @OnEvent('ai.health.checked')
    handleAIHealthChecked(payload: { healthy: boolean }): void {
        this.aiEngineStatus.set(payload.healthy ? 1 : 0);
    }

    // ==========================================
    // UTILITY METHODS
    // ==========================================

    recordHttpRequest(method: string, path: string, status: number, duration: number): void {
        const labels = { method, path: this.normalizePath(path), status: status.toString() };
        this.httpRequestsTotal.inc(labels);
        this.httpRequestDuration.observe(labels, duration);
    }

    setWebSocketConnections(count: number): void {
        this.websocketConnections.set(count);
    }

    recordRedisLatency(operation: string, duration: number): void {
        this.redisLatency.observe({ operation }, duration);
    }

    private normalizePath(path: string): string {
        if (!path) return 'unknown';
        return path
            .replace(/\/\d+/g, '/:id')
            .replace(/\/[a-f0-9-]{36}/g, '/:uuid');
    }
}
