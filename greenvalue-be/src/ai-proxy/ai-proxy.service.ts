import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
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
                image_key: params.imageKey,
                property_id: params.propertyId,
                user_id: params.userId,
                building_type: params.buildingType,
                building_year: params.buildingYear,
                confidence_threshold: params.confidenceThreshold,
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
    }): Promise<ReportResponse> {
        if (this.grpcClient.isGrpcConnected()) {
            try {
                return await this.grpcClient.generateReport(params);
            } catch (error) {
                if (!(error instanceof GrpcConnectionError)) throw error;
                this.logger.warn('gRPC failed, falling back to HTTP');
            }
        }

        const { data } = await firstValueFrom(
            this.httpService.post(`${this.aiEngineUrl}/api/v1/report`, {
                analysis_id: params.analysisId,
                format: params.format || 'PDF',
                include_renovations: params.includeRenovations ?? true,
            }),
        );

        return {
            reportId: data.report_id,
            fileKey: data.file_key,
            fileSize: data.file_size || 0,
            format: data.format || 'PDF',
        };
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
}
