import { Injectable, OnModuleInit, OnModuleDestroy, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as grpc from '@grpc/grpc-js';
import * as protoLoader from '@grpc/proto-loader';
import * as path from 'path';

/** gRPC response interfaces matching ai_service.proto */
export interface AnalyzeImageResponse {
    jobId: string;
    status: string;
}

export interface AnalysisStatusResponse {
    jobId: string;
    status: string;
    progress: number;
    detections: Array<{
        className: string;
        confidence: number;
        bbox: number[];
    }>;
    overallUValue: number;
    energyLabel: string;
    components: Array<{
        name: string;
        uValue: number;
        area: number;
        layers: string[];
    }>;
    renovations: Array<{
        component: string;
        currentUValue: number;
        improvedUValue: number;
        estimatedCost: number;
        annualSavings: number;
        paybackYears: number;
        co2ReductionKg: number;
    }>;
    heatmapKey: string;
    modelVersion: string;
    inferenceTimeMs: number;
    pipelineTimeMs: number;
    errorMessage: string;
}

export interface UValueResponse {
    uValue: number;
    energyLabel: string;
    totalResistance: number;
    layers: Array<{
        material: string;
        thickness: number;
        conductivity: number;
        resistance: number;
    }>;
}

export interface ReportResponse {
    reportId: string;
    fileKey: string;
    fileSize: number;
    format: string;
}

export interface SimilarPropertyResult {
    propertyId: string;
    similarityScore: number;
    address: string;
    energyLabel: string;
    overallUValue: number;
}

export interface FindSimilarResponse {
    properties: SimilarPropertyResult[];
}

export interface HealthCheckResponse {
    status: string;
    modelLoaded: boolean;
    modelVersion: string;
    device: string;
    gpuAvailable: boolean;
    totalAnalyses: number;
}

export class GrpcConnectionError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'GrpcConnectionError';
    }
}

@Injectable()
export class GrpcClientService implements OnModuleInit, OnModuleDestroy {
    private readonly logger = new Logger(GrpcClientService.name);
    private client: any;
    private connected = false;

    constructor(private readonly configService: ConfigService) {}

    async onModuleInit(): Promise<void> {
        await this.connect();
    }

    async onModuleDestroy(): Promise<void> {
        if (this.client) {
            grpc.closeClient(this.client);
            this.logger.log('gRPC client connection closed');
        }
    }

    private async connect(): Promise<void> {
        try {
            const protoPath = path.resolve(
                process.cwd(),
                this.configService.get('PROTO_PATH', 'proto/ai_service.proto'),
            );

            const packageDefinition = protoLoader.loadSync(protoPath, {
                keepCase: false,
                longs: String,
                enums: String,
                defaults: true,
                oneofs: true,
            });

            const grpcObject = grpc.loadPackageDefinition(packageDefinition);
            const greenValuePackage = (grpcObject as any).greenvalue?.v1;

            if (!greenValuePackage?.GreenValueAI) {
                this.logger.warn('GreenValueAI service not found in proto definition');
                return;
            }

            const host = this.configService.get('AI_ENGINE_GRPC_HOST', 'localhost');
            const port = this.configService.get('AI_ENGINE_GRPC_PORT', '50051');
            const address = `${host}:${port}`;

            this.client = new greenValuePackage.GreenValueAI(
                address,
                grpc.credentials.createInsecure(),
                {
                    'grpc.keepalive_time_ms': 15000,
                    'grpc.keepalive_timeout_ms': 5000,
                    'grpc.keepalive_permit_without_calls': 1,
                    'grpc.max_receive_message_length': 50 * 1024 * 1024,
                    'grpc.max_send_message_length': 50 * 1024 * 1024,
                },
            );

            // Wait for connection
            await new Promise<void>((resolve) => {
                const deadline = new Date(Date.now() + 5000);
                this.client.waitForReady(deadline, (error: Error | null) => {
                    if (error) {
                        this.logger.warn(`gRPC connection to AI Engine not ready: ${error.message}`);
                        this.connected = false;
                        resolve(); // Don't fail startup
                    } else {
                        this.connected = true;
                        this.logger.log(`✅ gRPC connected to AI Engine at ${address}`);
                        resolve();
                    }
                });
            });
        } catch (error) {
            this.logger.warn(`gRPC client initialization failed: ${(error as Error).message}`);
            this.connected = false;
        }
    }

    isGrpcConnected(): boolean {
        return this.connected;
    }

    private promisify<TReq, TRes>(method: string, request: TReq): Promise<TRes> {
        if (!this.client || !this.connected) {
            throw new GrpcConnectionError('gRPC client not connected');
        }

        return new Promise((resolve, reject) => {
            this.client[method](request, { deadline: new Date(Date.now() + 60000) }, (error: any, response: TRes) => {
                if (error) {
                    if (error.code === grpc.status.UNAVAILABLE) {
                        this.connected = false;
                        reject(new GrpcConnectionError(`AI Engine unavailable: ${error.message}`));
                    } else {
                        reject(error);
                    }
                } else {
                    resolve(response);
                }
            });
        });
    }

    // ==========================================
    // RPC Methods
    // ==========================================

    async analyzeImage(request: {
        imageKey: string;
        propertyId: string;
        userId: string;
        buildingType?: string;
        buildingYear?: number;
        confidenceThreshold?: number;
    }): Promise<AnalyzeImageResponse> {
        return this.promisify('AnalyzeImage', request);
    }

    async getAnalysisStatus(request: {
        jobId: string;
    }): Promise<AnalysisStatusResponse> {
        return this.promisify('GetAnalysisStatus', request);
    }

    async calculateUValue(request: {
        layers: string[];
        thicknesses?: number[];
        buildingYear?: number;
    }): Promise<UValueResponse> {
        return this.promisify('CalculateUValue', request);
    }

    async generateReport(request: {
        analysisId: string;
        format?: string;
        includeRenovations?: boolean;
    }): Promise<ReportResponse> {
        return this.promisify('GenerateReport', request);
    }

    async findSimilarProperties(request: {
        propertyId: string;
        limit?: number;
        minScore?: number;
    }): Promise<FindSimilarResponse> {
        return this.promisify('FindSimilarProperties', request);
    }

    async healthCheck(): Promise<HealthCheckResponse> {
        return this.promisify('HealthCheck', {});
    }
}
