import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import { PrismaService } from '../core/prisma/prisma.service';
import { StorageService } from '../core/storage/storage.service';
import {
    GrpcClientService,
    GrpcConnectionError,
    AnalysisStatusResponse,
    UValueResponse,
    ReportResponse,
    FindSimilarResponse,
    HealthCheckResponse,
} from './grpc-client.service';

@Injectable()
export class AIProxyService implements OnModuleInit {
    private readonly logger = new Logger(AIProxyService.name);
    private aiEngineUrl: string;

    constructor(
        private readonly grpcClient: GrpcClientService,
        private readonly httpService: HttpService,
        private readonly configService: ConfigService,
        private readonly prisma: PrismaService,
        private readonly storage: StorageService,
    ) {}

    async onModuleInit(): Promise<void> {
        this.aiEngineUrl = this.configService.get(
            'AI_ENGINE_URL',
            'http://ai-engine:8000',
        );
        this.logger.log(`✅ AI Proxy Service initialized (HTTP: ${this.aiEngineUrl})`);
    }

    // ==========================================
    // IMAGE ANALYSIS
    // ==========================================

    async analyzeImage(params: {
        imageKey: string;
        propertyId: string;
        userId: string;
        buildingType?: string;
        buildingYear?: number;
        confidenceThreshold?: number;
    }): Promise<{ jobId: string; status: string }> {
        // Try gRPC first
        if (this.grpcClient.isGrpcConnected()) {
            try {
                return await this.grpcClient.analyzeImage(params);
            } catch (error) {
                if (!(error instanceof GrpcConnectionError)) throw error;
                this.logger.warn('gRPC failed, falling back to HTTP');
            }
        }

        // HTTP fallback
        const { data } = await firstValueFrom(
            this.httpService.post(`${this.aiEngineUrl}/api/v1/analyze`, {
                file_key: params.imageKey,
                property_id: params.propertyId,
                model_size: null,
            }),
        );

        return { jobId: data.job_id, status: data.status || 'PENDING' };
    }

    async getAnalysisStatus(jobId: string): Promise<AnalysisStatusResponse> {
        if (this.grpcClient.isGrpcConnected()) {
            try {
                return await this.grpcClient.getAnalysisStatus({ jobId });
            } catch (error) {
                if (!(error instanceof GrpcConnectionError)) throw error;
                this.logger.warn('gRPC failed, falling back to HTTP');
            }
        }

        const { data } = await firstValueFrom(
            this.httpService.get(`${this.aiEngineUrl}/api/v1/analyze/${jobId}`),
        );

        return {
            jobId: data.job_id,
            status: data.status,
            progress: data.progress || 0,
            detections: data.detections || [],
            overallUValue: data.overall_u_value || 0,
            energyLabel: data.energy_label || '',
            components: data.components || [],
            renovations: data.renovations || [],
            heatmapKey: data.heatmap_key || '',
            modelVersion: data.model_version || '',
            inferenceTimeMs: data.inference_time_ms || 0,
            pipelineTimeMs: data.pipeline_time_ms || 0,
            errorMessage: data.error_message || '',
        };
    }

    // ==========================================
    // U-VALUE CALCULATION
    // ==========================================

    async calculateUValue(params: {
        layers: string[];
        thicknesses?: number[];
        buildingYear?: number;
    }): Promise<UValueResponse> {
        if (this.grpcClient.isGrpcConnected()) {
            try {
                return await this.grpcClient.calculateUValue(params);
            } catch (error) {
                if (!(error instanceof GrpcConnectionError)) throw error;
                this.logger.warn('gRPC failed, falling back to HTTP');
            }
        }

        const { data } = await firstValueFrom(
            this.httpService.post(`${this.aiEngineUrl}/api/v1/u-value`, {
                layers: params.layers,
                thicknesses_mm: params.thicknesses,
                building_year: params.buildingYear,
            }),
        );

        return {
            uValue: data.u_value,
            energyLabel: data.energy_label,
            totalResistance: data.total_resistance,
            layers: data.layers || [],
        };
    }

    // ==========================================
    // REPORT GENERATION
    // ==========================================

    async generateReport(params: {
        analysisId: string;
        format?: string;
        includeRenovations?: boolean;
    }): Promise<ReportResponse & { fileSize?: number }> {
        // 1. Load the full analysis from DB (the AI engine needs the actual result data)
        const analysis = await this.prisma.analysis.findUnique({
            where: { id: params.analysisId },
            include: { property: true },
        });

        if (!analysis) {
            throw new Error(`Analysis ${params.analysisId} not found in DB`);
        }

        const propertyId = analysis.propertyId;

        // Build the analysis_result dict the AI engine expects
        const analysisResult: Record<string, any> = {
            detections: analysis.detections ?? [],
            overall_u_value: analysis.overallUValue ?? 0,
            energy_label: analysis.energyLabel ?? '',
            components: analysis.components ?? [],
            renovations: analysis.renovations ?? [],
            heatmap_key: analysis.heatmapKey ?? '',
            model_version: analysis.modelVersion ?? '',
            inference_time_ms: analysis.inferenceTimeMs ?? 0,
            pipeline_time_ms: analysis.pipelineTimeMs ?? 0,
            address: analysis.property?.address ?? '',
        };

        // Map backend report format to AI engine report_type
        const reportTypeMap: Record<string, string> = {
            FULL_IVS: 'full_ivs',
            ENERGY_CERTIFICATE: 'energy_only',
            ROI_ANALYSIS: 'summary',
            COMPARISON: 'summary',
        };

        const reportType = reportTypeMap[params.format ?? 'FULL_IVS'] ?? 'full_ivs';

        // 2. Try gRPC first
        if (this.grpcClient.isGrpcConnected()) {
            try {
                return await this.grpcClient.generateReport(params);
            } catch (error) {
                if (!(error instanceof GrpcConnectionError)) throw error;
                this.logger.warn('gRPC failed, falling back to HTTP');
            }
        }

        // 3. HTTP fallback — call /api/v1/report/generate/pdf for raw PDF bytes
        this.logger.log(`Requesting PDF from AI engine for analysis ${params.analysisId}`);

        const { data: pdfArrayBuffer } = await firstValueFrom(
            this.httpService.post(
                `${this.aiEngineUrl}/api/v1/report/generate/pdf`,
                {
                    property_id: propertyId,
                    report_type: reportType,
                    language: 'en',
                    include_heatmap: true,
                    include_charts: true,
                    analysis_result: analysisResult,
                },
                { responseType: 'arraybuffer', timeout: 300_000 },
            ),
        );

        const pdfBuffer = Buffer.from(pdfArrayBuffer);
        this.logger.log(`Received PDF (${pdfBuffer.length} bytes) from AI engine`);

        // 4. Upload the PDF to MinIO via StorageService
        const fileKey = `${propertyId}/${params.analysisId}.pdf`;
        const bucket = 'pdf-reports';

        await this.storage.upload(bucket, fileKey, pdfBuffer, {
            'Content-Type': 'application/pdf',
        });

        this.logger.log(`Uploaded report PDF to MinIO: ${bucket}/${fileKey}`);

        const reportId = `GV-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}-${params.analysisId.slice(0, 8)}`;

        return {
            reportId,
            fileKey: `${bucket}/${fileKey}`,
            fileSize: pdfBuffer.length,
            format: (params.format as string) || 'PDF',
        } as any;
    }

    // ==========================================
    // SIMILAR PROPERTIES
    // ==========================================

    async findSimilarProperties(params: {
        propertyId: string;
        limit?: number;
        minScore?: number;
    }): Promise<FindSimilarResponse> {
        if (this.grpcClient.isGrpcConnected()) {
            try {
                return await this.grpcClient.findSimilarProperties(params);
            } catch (error) {
                if (!(error instanceof GrpcConnectionError)) throw error;
                this.logger.warn('gRPC failed, falling back to HTTP');
            }
        }

        const { data } = await firstValueFrom(
            this.httpService.post(`${this.aiEngineUrl}/api/v1/similar`, {
                property_id: params.propertyId,
                limit: params.limit || 5,
                min_score: params.minScore || 0.7,
            }),
        );

        return { properties: data.properties || [] };
    }

    // ==========================================
    // HEALTH CHECK
    // ==========================================

    async getAIHealth(): Promise<HealthCheckResponse> {
        if (this.grpcClient.isGrpcConnected()) {
            try {
                return await this.grpcClient.healthCheck();
            } catch (error) {
                if (!(error instanceof GrpcConnectionError)) throw error;
            }
        }

        try {
            const { data } = await firstValueFrom(
                this.httpService.get(`${this.aiEngineUrl}/health`),
            );
            return {
                status: data.status || 'unknown',
                modelLoaded: data.model_loaded || false,
                modelVersion: data.model_version || '',
                device: data.device || '',
                gpuAvailable: data.gpu_available || false,
                totalAnalyses: data.total_analyses || 0,
            };
        } catch {
            return {
                status: 'unavailable',
                modelLoaded: false,
                modelVersion: '',
                device: '',
                gpuAvailable: false,
                totalAnalyses: 0,
            };
        }
    }

    // ==========================================
    // MATERIALS LIST
    // ==========================================

    async getMaterials(): Promise<any> {
        try {
            const { data } = await firstValueFrom(
                this.httpService.get(`${this.aiEngineUrl}/api/v1/materials`),
            );
            return data;
        } catch (error) {
            this.logger.warn(`Failed to get materials: ${(error as Error).message}`);
            return { materials: [] };
        }
    }

    // ==========================================
    // PROPERTY GRAPH
    // ==========================================

    async getPropertyGraph(request: {
        propertyId: string;
        query?: string;
        improvementTypes?: string[];
    }): Promise<any> {
        if (this.grpcClient.isGrpcConnected()) {
            try {
                return await this.grpcClient.getPropertyGraph(request);
            } catch (error) {
                if (!(error instanceof GrpcConnectionError)) throw error;
                this.logger.warn('gRPC failed for getPropertyGraph, falling back to HTTP');
            }
        }

        try {
            const { data } = await firstValueFrom(
                this.httpService.post(`${this.aiEngineUrl}/api/v1/graph/property`, request),
            );
            return data;
        } catch (error) {
            this.logger.warn(`Failed to get property graph: ${(error as Error).message}`);
            return { relations: [], rippleEffects: [], relatedFactors: [], summary: '' };
        }
    }

    // ==========================================
    // CHAIN-OF-THOUGHT ANALYSIS
    // ==========================================

    async chainOfThoughtAnalysis(request: {
        propertyId: string;
        detections: any[];
        uValues: any[];
        energyLabel?: string;
        propertyMeta?: Record<string, string>;
    }): Promise<any> {
        if (this.grpcClient.isGrpcConnected()) {
            try {
                return await this.grpcClient.chainOfThoughtAnalysis(request);
            } catch (error) {
                if (!(error instanceof GrpcConnectionError)) throw error;
                this.logger.warn('gRPC failed for chainOfThought, falling back to HTTP');
            }
        }

        try {
            const { data } = await firstValueFrom(
                this.httpService.post(`${this.aiEngineUrl}/api/v1/report/chain-of-thought`, request),
            );
            return data;
        } catch (error) {
            this.logger.warn(`Failed chain-of-thought analysis: ${(error as Error).message}`);
            return { success: false, error: (error as Error).message, upgrades: [] };
        }
    }

    // ==========================================
    // PERSIST ANALYSIS RESULT TO DB
    // ==========================================

    /**
     * Upsert a completed analysis result to Prisma `analyses` table.
     * Called automatically when getAnalysisStatus returns COMPLETED.
     * Returns the Prisma Analysis UUID (`id`).
     */
    async persistCompletedAnalysis(params: {
        jobId: string;
        propertyId: string;
        userId: string;
        imageKey: string;
        result: AnalysisStatusResponse;
    }): Promise<string> {
        const { jobId, propertyId, userId, imageKey, result } = params;

        // Check if already exists
        const existing = await this.prisma.analysis.findUnique({
            where: { jobId },
            select: { id: true },
        });
        if (existing) return existing.id;

        const analysis = await this.prisma.analysis.create({
            data: {
                jobId,
                status: 'COMPLETED' as any,
                imageKey,
                heatmapKey: result.heatmapKey || null,
                detections: (result.detections as any) ?? [],
                inferenceTimeMs: result.inferenceTimeMs || null,
                overallUValue: result.overallUValue || null,
                energyLabel: this._mapEnergyLabel(result.energyLabel),
                components: (result.components as any) ?? [],
                renovations: (result.renovations as any) ?? [],
                modelVersion: result.modelVersion || null,
                device: 'cuda',
                pipelineTimeMs: result.pipelineTimeMs || null,
                propertyId,
                userId,
            },
        });

        this.logger.log(`Analysis persisted: ${analysis.id} (jobId=${jobId})`);
        return analysis.id;
    }

    private _mapEnergyLabel(label: string | undefined | null): any {
        if (!label) return null;
        const map: Record<string, string> = {
            'A+': 'A_PLUS', 'A_PLUS': 'A_PLUS',
            'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D', 'E': 'E', 'F': 'F', 'G': 'G',
        };
        return map[label] ?? label;
    }
}
