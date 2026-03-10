import {
    Controller,
    Get,
    Post,
    Delete,
    Param,
    Body,
    Query,
    UseGuards,
    HttpCode,
    HttpStatus,
    ParseUUIDPipe,
} from '@nestjs/common';
import {
    ApiTags,
    ApiBearerAuth,
    ApiOperation,
    ApiResponse,
    ApiParam,
} from '@nestjs/swagger';
import { ReportService } from './report.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { CurrentUser } from '../common/decorators/roles.decorator';
import { GenerateReportDto, ReportListQueryDto, ReportResponseDto } from './dto';

@ApiTags('Reports')
@Controller('reports')
@UseGuards(JwtAuthGuard)
@ApiBearerAuth()
export class ReportController {
    constructor(private readonly reportService: ReportService) {}

    // ── Generate ─────────────────────────────────

    @Post()
    @HttpCode(HttpStatus.CREATED)
    @ApiOperation({ summary: 'Generate a new report from an analysis' })
    @ApiResponse({ status: 201, description: 'Report generation enqueued', type: ReportResponseDto })
    async generate(
        @CurrentUser('id') userId: string,
        @Body() dto: GenerateReportDto,
    ) {
        return this.reportService.generate(userId, dto);
    }

    // ── My Reports ───────────────────────────────

    @Get()
    @ApiOperation({ summary: 'List my reports' })
    async findMyReports(
        @CurrentUser('id') userId: string,
        @Query() query: ReportListQueryDto,
    ) {
        return this.reportService.findMyReports(userId, query);
    }

    // ── Reports by Property (static prefix — must be above :id) ──

    @Get('property/:propertyId')
    @ApiOperation({ summary: 'List reports for a specific property' })
    @ApiParam({ name: 'propertyId', type: 'string' })
    async findByProperty(
        @CurrentUser('id') userId: string,
        @Param('propertyId', ParseUUIDPipe) propertyId: string,
        @Query() query: ReportListQueryDto,
    ) {
        return this.reportService.findByProperty(propertyId, userId, query);
    }

    // ── Get by ID ────────────────────────────────

    @Get(':id')
    @ApiOperation({ summary: 'Get report details (includes download URL)' })
    @ApiParam({ name: 'id', type: 'string' })
    async findById(
        @CurrentUser('id') userId: string,
        @Param('id', ParseUUIDPipe) id: string,
    ) {
        return this.reportService.findById(id, userId);
    }

    // ── Preview (metadata + analysis data) ───────

    @Get(':id/preview')
    @ApiOperation({ summary: 'Get report preview with analysis data and chain-of-thought log' })
    @ApiParam({ name: 'id', type: 'string' })
    async preview(
        @CurrentUser('id') userId: string,
        @Param('id', ParseUUIDPipe) id: string,
    ) {
        return this.reportService.preview(id, userId);
    }

    // ── Delete ───────────────────────────────────

    @Delete(':id')
    @HttpCode(HttpStatus.OK)
    @ApiOperation({ summary: 'Delete a report and its file from storage' })
    @ApiParam({ name: 'id', type: 'string' })
    async remove(
        @CurrentUser('id') userId: string,
        @Param('id', ParseUUIDPipe) id: string,
    ) {
        return this.reportService.remove(id, userId);
    }
}
