import {
    Injectable,
    Logger,
    NotFoundException,
    BadRequestException,
} from '@nestjs/common';
import { PrismaService } from '../core/prisma/prisma.service';
import { StorageService } from '../core/storage/storage.service';
import { QueueService } from '../core/bullmq/queue.service';
import { AIProxyService } from '../ai-proxy/ai-proxy.service';
import { GenerateReportDto, ReportListQueryDto } from './dto';
import { ReportFormat } from '@prisma/client';

/**
 * NOTE: After running `npx prisma migrate dev` and `npx prisma generate`,
 * remove all `as any` casts — the new fields (reportType, language,
 * generationTimeMs, ivsComplianceWarnings, chainOfThoughtLog) will be
 * recognized by the Prisma client types.
 */

@Injectable()
export class ReportService {
    private readonly logger = new Logger(ReportService.name);

    constructor(
        private readonly prisma: PrismaService,
        private readonly storage: StorageService,
        private readonly queue: QueueService,
        private readonly aiProxy: AIProxyService,
    ) {}

    // ──────────────────────────────────────────────
    // Generate Report (enqueues via BullMQ)
    // ──────────────────────────────────────────────

    async generate(userId: string, dto: GenerateReportDto) {
        // 1. Verify the analysis exists and belongs to user
        const analysis = await this.prisma.analysis.findUnique({
            where: { id: dto.analysisId },
            include: { property: true },
        });

        if (!analysis) {
            throw new NotFoundException(`Analysis ${dto.analysisId} not found`);
        }
        if (analysis.userId !== userId) {
            throw new BadRequestException('You do not own this analysis');
        }

        // 2. Check for existing report
        const existing = await this.prisma.report.findUnique({
            where: { analysisId: dto.analysisId },
        });
        if (existing) {
            this.logger.log(`Report already exists for analysis ${dto.analysisId}: ${existing.id}`);
            return this._toResponse(existing);
        }

        // 3. Create a placeholder report record
        // `reportType` and `language` are new Prisma fields — cast until migration
        const report = await (this.prisma.report as any).create({
            data: {
                format: dto.format || ReportFormat.PDF,
                reportType: dto.reportType || 'FULL_IVS',
                language: dto.language || 'en',
                fileKey: '',
                title: `${analysis.property.title || 'Property'} — ${dto.reportType || 'FULL_IVS'} Report`,
                analysisId: dto.analysisId,
                propertyId: analysis.propertyId,
                userId,
            },
        });

        // 4. Enqueue report generation via BullMQ
        await this.queue.addReportJob({
            analysisId: dto.analysisId,
            userId,
            format: ((dto.format as string) || 'PDF') as 'PDF' | 'DOCX',
            locale: dto.language || 'en',
        });

        this.logger.log(`Report ${report.id} queued for analysis ${dto.analysisId}`);

        return this._toResponse(report);
    }

    async processReportJob(data: {
        analysisId: string;
        userId: string;
        format: string;
        locale: string;
    }) {
        const startMs = Date.now();

        try {
            const report = await this.prisma.report.findUnique({
                where: { analysisId: data.analysisId },
                include: { analysis: true },
            });

            if (!report) {
                this.logger.error(`No report record for analysis ${data.analysisId}`);
                return;
            }

            
            const reportType = (report as any).reportType || 'FULL_IVS';
            const aiResult = await this.aiProxy.generateReport({
                analysisId: data.analysisId,
                format: reportType,          
                includeRenovations: true,
            });

            if (!aiResult?.fileKey && !aiResult?.reportId) {
                throw new Error('AI Engine returned no report result');
            }

            const fileKey = aiResult.fileKey || `pdf-reports/${report.propertyId}/${report.id}.pdf`;

            
            let fileSize: number | null = (aiResult as any).fileSize ?? null;
            if (!fileSize) {
                try {
                    // fileKey may be "pdf-reports/propId/analysisId.pdf" — strip bucket prefix for stat()
                    const keyInBucket = fileKey.startsWith('pdf-reports/')
                        ? fileKey.replace('pdf-reports/', '')
                        : fileKey;
                    const stat = await this.storage.stat('pdf-reports', keyInBucket);
                    fileSize = stat.size;
                } catch {
                    this.logger.warn(`Report file not found in storage: ${fileKey}`);
                }
            }

            const generationTimeMs = Date.now() - startMs;

            // Update the report record — `generationTimeMs` is a new field
            await (this.prisma.report as any).update({
                where: { id: report.id },
                data: {
                    fileKey,
                    fileSize,
                    generationTimeMs,
                },
            });

            this.logger.log(
                `Report ${report.id} generated in ${generationTimeMs}ms — key: ${fileKey}`,
            );
        } catch (error) {
            this.logger.error(
                `Report generation failed for analysis ${data.analysisId}: ${(error as Error).message}`,
            );
            // Keep the report record so BullMQ retries can find it
            throw error;
        }
    }

    // ──────────────────────────────────────────────
    // CRUD
    // ──────────────────────────────────────────────

    async findById(reportId: string, userId: string) {
        const report = await this.prisma.report.findUnique({
            where: { id: reportId },
        });

        if (!report || report.userId !== userId) {
            throw new NotFoundException(`Report ${reportId} not found`);
        }

        let downloadUrl: string | undefined;
        if (report.fileKey) {
            try {
                const objectKey = report.fileKey.replace('pdf-reports/', '');
                downloadUrl = await this.storage.getPresignedDownloadUrl(
                    'pdf-reports',
                    objectKey,
                    3600,
                );
            } catch {
                this.logger.warn(`Could not generate download URL for ${report.fileKey}`);
            }
        }

        return { ...this._toResponse(report), downloadUrl };
    }

    async findByProperty(propertyId: string, userId: string, query: ReportListQueryDto) {
        const { page = 1, limit = 20, format, reportType } = query;

        const where: any = { propertyId, userId };
        if (format) where.format = format;
        if (reportType) where.reportType = reportType;

        const [reports, total] = await Promise.all([
            this.prisma.report.findMany({
                where,
                orderBy: { createdAt: 'desc' },
                skip: (page - 1) * limit,
                take: limit,
            }),
            this.prisma.report.count({ where }),
        ]);

        return {
            data: reports.map((r: any) => this._toResponse(r)),
            meta: { total, page, limit, totalPages: Math.ceil(total / limit) },
        };
    }

    async findMyReports(userId: string, query: ReportListQueryDto) {
        const { page = 1, limit = 20, format, reportType, propertyId } = query;

        const where: any = { userId };
        if (format) where.format = format;
        if (reportType) where.reportType = reportType;
        if (propertyId) where.propertyId = propertyId;

        const [reports, total] = await Promise.all([
            this.prisma.report.findMany({
                where,
                orderBy: { createdAt: 'desc' },
                skip: (page - 1) * limit,
                take: limit,
                include: { property: { select: { id: true, title: true, address: true } } },
            }),
            this.prisma.report.count({ where }),
        ]);

        return {
            data: reports.map((r: any) => this._toResponse(r)),
            meta: { total, page, limit, totalPages: Math.ceil(total / limit) },
        };
    }

    async preview(reportId: string, userId: string) {
        const report: any = await this.prisma.report.findUnique({
            where: { id: reportId },
            include: {
                analysis: {
                    select: {
                        detections: true,
                        overallUValue: true,
                        energyLabel: true,
                        components: true,
                        renovations: true,
                    },
                },
            },
        });

        if (!report || report.userId !== userId) {
            throw new NotFoundException(`Report ${reportId} not found`);
        }

        return {
            report: this._toResponse(report),
            ivsComplianceWarnings: report.ivsComplianceWarnings ?? null,
            chainOfThoughtLog: report.chainOfThoughtLog ?? null,
            analysis: report.analysis,
        };
    }

    async remove(reportId: string, userId: string) {
        const report = await this.prisma.report.findUnique({
            where: { id: reportId },
        });

        if (!report || report.userId !== userId) {
            throw new NotFoundException(`Report ${reportId} not found`);
        }

        if (report.fileKey) {
            try {
                const objectKey = report.fileKey.replace('pdf-reports/', '');
                await this.storage.delete('pdf-reports', objectKey);
            } catch {
                this.logger.warn(`Failed to delete storage file: ${report.fileKey}`);
            }
        }

        await this.prisma.report.delete({ where: { id: reportId } });

        return { deleted: true, id: reportId };
    }

    // ──────────────────────────────────────────────
    // Private helpers
    // ──────────────────────────────────────────────

    private _toResponse(report: any) {
        return {
            id: report.id,
            format: report.format,
            reportType: report.reportType ?? null,
            title: report.title,
            fileKey: report.fileKey,
            fileSize: report.fileSize,
            language: report.language ?? 'en',
            generationTimeMs: report.generationTimeMs ?? null,
            analysisId: report.analysisId,
            propertyId: report.propertyId,
            userId: report.userId,
            createdAt: report.createdAt,
            property: report.property ?? undefined,
        };
    }
}
