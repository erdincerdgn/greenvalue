import {
    Controller,
    Get,
    Post,
    Body,
    Param,
    UseGuards,
    Request,
    Logger,
    HttpCode,
    HttpStatus,
} from '@nestjs/common';
import {
    ApiTags,
    ApiOperation,
    ApiResponse,
    ApiBearerAuth,
    ApiBody,
    ApiParam,
} from '@nestjs/swagger';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { AIProxyService } from './ai-proxy.service';
import {
    AnalyzeImageDto,
    CalculateUValueDto,
    FindSimilarDto,
    GenerateReportDto,
    AnalysisStatusResponseDto,
    UValueResultDto,
    ReportResponseDto,
    AIHealthResponseDto,
} from './dto/ai-proxy.dto';

@ApiTags('Analysis')
@Controller('api/v1/analysis')
export class AIProxyController {
    private readonly logger = new Logger(AIProxyController.name);

    constructor(private readonly aiProxyService: AIProxyService) {}

    // ==========================================
    // IMAGE ANALYSIS
    // ==========================================

    @Post('analyze')
    @UseGuards(JwtAuthGuard)
    @ApiBearerAuth('JWT')
    @HttpCode(HttpStatus.ACCEPTED)
    @ApiOperation({
        summary: 'Submit an image for AI analysis',
        description:
            'Submits a building image (already uploaded to MinIO) for YOLO11 detection, U-Value calculation, energy labelling, and heatmap generation. Returns a job ID for polling.',
    })
    @ApiResponse({ status: 202, description: 'Analysis job queued', type: AnalysisStatusResponseDto })
    @ApiBody({ type: AnalyzeImageDto })
    async analyzeImage(
        @Body() dto: AnalyzeImageDto,
        @Request() req,
    ): Promise<AnalysisStatusResponseDto> {
        const userId = req.user.id;

        this.logger.log(
            `Analysis requested: property=${dto.propertyId}, user=${userId}`,
        );

        const result = await this.aiProxyService.analyzeImage({
            imageKey: dto.imageKey,
            propertyId: dto.propertyId,
            userId,
            buildingType: dto.buildingType,
            buildingYear: dto.buildingYear,
            confidenceThreshold: dto.confidenceThreshold,
        });

        return {
            jobId: result.jobId,
            status: result.status as any,
        };
    }

    @Get('status/:jobId')
    @UseGuards(JwtAuthGuard)
    @ApiBearerAuth('JWT')
    @ApiOperation({
        summary: 'Get analysis job status and results',
        description:
            'Poll this endpoint with the job ID returned from /analyze. Returns detection results, U-Values, energy label, and heatmap when complete.',
    })
    @ApiParam({ name: 'jobId', description: 'Analysis job ID' })
    @ApiResponse({ status: 200, description: 'Analysis status/result' })
    async getAnalysisStatus(
        @Param('jobId') jobId: string,
    ): Promise<AnalysisStatusResponseDto> {
        const result = await this.aiProxyService.getAnalysisStatus(jobId);

        return {
            jobId: result.jobId,
            status: result.status as any,
            progress: result.progress,
            result:
                result.status === 'COMPLETED'
                    ? {
                          jobId: result.jobId,
                          detections: result.detections,
                          overallUValue: result.overallUValue,
                          energyLabel: result.energyLabel as any,
                          components: result.components,
                          renovations: result.renovations,
                          heatmapKey: result.heatmapKey,
                          modelVersion: result.modelVersion,
                          inferenceTimeMs: result.inferenceTimeMs,
                          pipelineTimeMs: result.pipelineTimeMs,
                      }
                    : undefined,
            errorMessage: result.errorMessage || undefined,
        };
    }

    // ==========================================
    // U-VALUE CALCULATION
    // ==========================================

    @Post('u-value')
    @UseGuards(JwtAuthGuard)
    @ApiBearerAuth('JWT')
    @ApiOperation({
        summary: 'Calculate U-Value for a wall assembly',
        description:
            'Calculate U-Value (thermal transmittance) for a given set of material layers based on EN ISO 6946.',
    })
    @ApiResponse({ status: 200, description: 'U-Value calculation result', type: UValueResultDto })
    @ApiBody({ type: CalculateUValueDto })
    async calculateUValue(@Body() dto: CalculateUValueDto): Promise<UValueResultDto> {
        const result = await this.aiProxyService.calculateUValue({
            layers: dto.layers,
            thicknesses: dto.thicknesses,
            buildingYear: dto.buildingYear,
        });

        return {
            uValue: result.uValue,
            energyLabel: result.energyLabel as any,
            totalResistance: result.totalResistance,
            layers: result.layers,
        };
    }

    @Get('materials')
    @ApiOperation({
        summary: 'Get available building materials',
        description: 'Returns all materials available for U-Value calculations with thermal properties.',
    })
    @ApiResponse({ status: 200, description: 'Material list' })
    async getMaterials() {
        return this.aiProxyService.getMaterials();
    }

    // ==========================================
    // SIMILAR PROPERTIES
    // ==========================================

    @Post('similar')
    @UseGuards(JwtAuthGuard)
    @ApiBearerAuth('JWT')
    @ApiOperation({
        summary: 'Find similar properties ("Homes Like This")',
        description:
            'Uses Qdrant vector similarity search to find properties with similar building characteristics and energy profiles.',
    })
    @ApiResponse({ status: 200, description: 'Similar properties list' })
    @ApiBody({ type: FindSimilarDto })
    async findSimilarProperties(@Body() dto: FindSimilarDto) {
        const result = await this.aiProxyService.findSimilarProperties({
            propertyId: dto.propertyId,
            limit: dto.limit,
            minScore: dto.minScore,
        });

        return result;
    }

    // ==========================================
    // REPORT GENERATION
    // ==========================================

    @Post('report')
    @UseGuards(JwtAuthGuard)
    @ApiBearerAuth('JWT')
    @HttpCode(HttpStatus.CREATED)
    @ApiOperation({
        summary: 'Generate analysis report (PDF/JSON)',
        description:
            'Generates a comprehensive energy analysis report including detection results, U-Values, energy labels, and renovation ROI.',
    })
    @ApiResponse({ status: 201, description: 'Report generated', type: ReportResponseDto })
    @ApiBody({ type: GenerateReportDto })
    async generateReport(@Body() dto: GenerateReportDto): Promise<ReportResponseDto> {
        const result = await this.aiProxyService.generateReport({
            analysisId: dto.analysisId,
            format: dto.format,
            includeRenovations: dto.includeRenovations,
        });

        return {
            reportId: result.reportId,
            fileKey: result.fileKey,
            fileSize: result.fileSize,
            format: result.format,
        };
    }

    // ==========================================
    // AI ENGINE HEALTH
    // ==========================================

    @Get('ai-health')
    @ApiOperation({
        summary: 'Check AI Engine health status',
        description: 'Returns AI Engine status, loaded model, GPU availability, and analysis counters.',
    })
    @ApiResponse({ status: 200, description: 'AI Engine health', type: AIHealthResponseDto })
    async getAIHealth(): Promise<AIHealthResponseDto> {
        return this.aiProxyService.getAIHealth();
    }
}
