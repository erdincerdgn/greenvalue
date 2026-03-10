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

// ── Property Graph ──

export interface GraphRelation {
    source: string;
    relation: string;
    target: string;
    confidence: number;
}

export interface RippleEffect {
    improvement: string;
    factor: string;
    changePercent: number;
}

export interface GetPropertyGraphResponse {
    relations: GraphRelation[];
    rippleEffects: RippleEffect[];
    relatedFactors: string[];
    summary: string;
}

// ── Chain-of-Thought ──

export interface UpgradeRecommendation {
    component: string;
    action: string;
    cost: number;
    valueAdd: number;
    roiPercent: number;
    paybackYears: number;
    energySavingsKwh: number;
    co2ReductionKg: number;
    bookSource: string;
}

export interface StepLog {
    stepName: string;
    bookId: string;
    queryUsed: string;
    chunksRetrieved: number;
    durationSeconds: number;
    summary: string;
}

export interface ChainOfThoughtResponse {
    success: boolean;
    upgrades: UpgradeRecommendation[];
    totalCost: number;
    totalValueAdd: number;
    aggregateRoi: number;
    labelBefore: string;
    labelAfter: string;
    stepLogs: StepLog[];
    durationSeconds: number;
    error: string;
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

    constructor(private readonly configService: ConfigService) { }

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
            const greenValuePackage = (grpcObject as any).greenvalue?.ai?.v1;

            if (!greenValuePackage?.AIService) {
                this.logger.warn('AIService not found in proto definition');
                return;
            }

            const host = this.configService.get('AI_GRPC_HOST', 'localhost');
            const port = this.configService.get('AI_GRPC_PORT', '50051');
            const address = `${host}:${port}`;

            this.client = new greenValuePackage.AIService(
                address,
                grpc.credentials.createInsecure(),
                {
                    'grpc.keepalive_time_ms': 120000,
                    'grpc.keepalive_timeout_ms': 20000,
                    'grpc.keepalive_permit_without_calls': 0,
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
        // Map DTO field names to proto camelCase equivalents
        // Proto: file_key → JS (keepCase:false): fileKey
        const grpcRequest = {
            fileKey: request.imageKey,
            propertyId: request.propertyId,
            userId: request.userId,
            buildingType: request.buildingType,
            buildingYear: request.buildingYear,
            confidenceThreshold: request.confidenceThreshold,
        };
        const raw: any = await this.promisify('AnalyzeImage', grpcRequest);
        return {
            jobId: raw.jobId || '',
            status: this.mapAnalysisStatus(raw.status),
        };
    }

    async getAnalysisStatus(request: {
        jobId: string;
    }): Promise<AnalysisStatusResponse> {
        const raw: any = await this.promisify('GetAnalysisStatus', request);
        // gRPC response has nested 'result' (AnalysisResult). Flatten into our interface.
        const r = raw.result || {};
        return {
            jobId: raw.jobId || request.jobId,
            status: this.mapAnalysisStatus(raw.status),
            progress: raw.progressPercent || 0,
            detections: (r.detections || []).map((d: any) => ({
                className: d.className || '',
                confidence: d.confidence || 0,
                bbox: d.bbox
                    ? [d.bbox.xMin, d.bbox.yMin, d.bbox.xMax, d.bbox.yMax]
                    : [],
            })),
            overallUValue: r.overallUValue || 0,
            energyLabel: r.energyLabel || '',
            components: r.components || [],
            renovations: r.renovations || [],
            heatmapKey: r.heatmapKey || '',
            modelVersion: r.modelVersion || '',
            inferenceTimeMs: r.inferenceTimeMs || 0,
            pipelineTimeMs: 0,
            errorMessage: raw.errorMessage || '',
        };
    }

    /** Map gRPC AnalysisStatus enum (0-4) to string label */
    private mapAnalysisStatus(status: number | string): string {
        const map: Record<number, string> = {
            0: 'UNKNOWN',
            1: 'QUEUED',
            2: 'PROCESSING',
            3: 'COMPLETED',
            4: 'FAILED',
        };
        return typeof status === 'string' ? status : map[status] || 'UNKNOWN';
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

    async getPropertyGraph(request: {
        propertyId: string;
        query?: string;
        improvementTypes?: string[];
    }): Promise<GetPropertyGraphResponse> {
        return this.promisify('GetPropertyGraph', request);
    }

    async chainOfThoughtAnalysis(request: {
        propertyId: string;
        detections: Array<{
            className: string;
            confidence: number;
            areaM2: number;
            condition: string;
            uValue: number;
        }>;
        uValues: Array<{
            componentType: string;
            uValue: number;
            areaM2: number;
            heatLossKwh: number;
        }>;
        energyLabel?: string;
        propertyMeta?: Record<string, string>;
    }): Promise<ChainOfThoughtResponse> {
        return this.promisify('ChainOfThoughtAnalysis', request);
    }
}
