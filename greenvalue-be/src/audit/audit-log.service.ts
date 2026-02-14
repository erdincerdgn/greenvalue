import { Injectable, Logger } from '@nestjs/common';
import { OnEvent } from '@nestjs/event-emitter';
import { PrismaService } from '../core/prisma/prisma.service';

/**
 * Audit Action Types for GreenValue AI Platform
 */
export enum AuditAction {
    // Property events
    PROPERTY_CREATED = 'PROPERTY_CREATED',
    PROPERTY_UPDATED = 'PROPERTY_UPDATED',
    PROPERTY_DELETED = 'PROPERTY_DELETED',

    // Analysis events
    ANALYSIS_CREATED = 'ANALYSIS_CREATED',
    ANALYSIS_STARTED = 'ANALYSIS_STARTED',
    ANALYSIS_COMPLETED = 'ANALYSIS_COMPLETED',
    ANALYSIS_FAILED = 'ANALYSIS_FAILED',

    // U-Value events
    UVALUE_CALCULATED = 'UVALUE_CALCULATED',

    // Report events
    REPORT_GENERATED = 'REPORT_GENERATED',
    REPORT_DOWNLOADED = 'REPORT_DOWNLOADED',

    // Account events
    USER_REGISTERED = 'USER_REGISTERED',
    USER_LOGIN = 'USER_LOGIN',
    USER_PROFILE_UPDATED = 'USER_PROFILE_UPDATED',
    PASSWORD_CHANGED = 'PASSWORD_CHANGED',

    // Admin events
    USER_ROLE_CHANGED = 'USER_ROLE_CHANGED',
    USER_DEACTIVATED = 'USER_DEACTIVATED',

    // System events
    SYSTEM_ERROR = 'SYSTEM_ERROR',
    CONFIG_CHANGED = 'CONFIG_CHANGED',
}

export interface AuditEntry {
    userId: string;
    action: AuditAction;
    entity?: string;
    entityId?: string;
    metadata?: Record<string, any>;
    ipAddress?: string;
    userAgent?: string;
}

/**
 * Audit Log Service for GreenValue AI Platform
 *
 * Immutable audit trail for:
 * - Property management actions
 * - Analysis lifecycle
 * - Report generation
 * - User account events
 */
@Injectable()
export class AuditLogService {
    private readonly logger = new Logger(AuditLogService.name);

    constructor(private readonly prisma: PrismaService) {}

    // ==========================================
    // CORE LOGGING
    // ==========================================

    async log(entry: AuditEntry): Promise<void> {
        try {
            await this.prisma.auditLog.create({
                data: {
                    userId: entry.userId,
                    action: entry.action,
                    entity: entry.entity,
                    entityId: entry.entityId,
                    metadata: entry.metadata ? JSON.parse(JSON.stringify(entry.metadata)) : undefined,
                    ip: entry.ipAddress,
                    userAgent: entry.userAgent,
                },
            });

            this.logger.debug(`Audit: ${entry.action} for user ${entry.userId}`);
        } catch (error) {
            this.logger.warn(`Audit (fallback): ${entry.action} - ${JSON.stringify(entry.metadata)}`);
        }
    }

    // ==========================================
    // CONVENIENCE LOG METHODS
    // ==========================================

    async logPropertyEvent(
        userId: string,
        action: AuditAction,
        propertyId: string,
        details?: Record<string, any>,
        ipAddress?: string,
    ): Promise<void> {
        await this.log({
            userId,
            action,
            entity: 'Property',
            entityId: propertyId,
            metadata: details,
            ipAddress,
        });
    }

    async logAnalysisEvent(
        userId: string,
        action: AuditAction,
        analysisId: string,
        details?: Record<string, any>,
    ): Promise<void> {
        await this.log({
            userId,
            action,
            entity: 'Analysis',
            entityId: analysisId,
            metadata: details,
        });
    }

    async logReportEvent(
        userId: string,
        action: AuditAction,
        reportId: string,
        details?: Record<string, any>,
    ): Promise<void> {
        await this.log({
            userId,
            action,
            entity: 'Report',
            entityId: reportId,
            metadata: details,
        });
    }

    async logUserEvent(
        userId: string,
        action: AuditAction,
        details?: Record<string, any>,
        ipAddress?: string,
        userAgent?: string,
    ): Promise<void> {
        await this.log({
            userId,
            action,
            entity: 'User',
            entityId: userId,
            metadata: details,
            ipAddress,
            userAgent,
        });
    }

    // ==========================================
    // QUERY
    // ==========================================

    async getUserAuditHistory(
        userId: string,
        options?: {
            action?: AuditAction;
            entity?: string;
            startDate?: Date;
            endDate?: Date;
            limit?: number;
        },
    ) {
        const limit = options?.limit || 100;
        const startDate = options?.startDate || new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
        const endDate = options?.endDate || new Date();

        return this.prisma.auditLog.findMany({
            where: {
                userId,
                ...(options?.action && { action: options.action }),
                ...(options?.entity && { entity: options.entity }),
                createdAt: {
                    gte: startDate,
                    lte: endDate,
                },
            },
            orderBy: { createdAt: 'desc' },
            take: limit,
        });
    }

    /**
     * Export audit logs for a user
     */
    async exportAuditLogs(
        userId: string,
        startDate: Date,
        endDate: Date,
    ) {
        const logs = await this.getUserAuditHistory(userId, {
            startDate,
            endDate,
            limit: 10000,
        });

        const analysisLogs = logs.filter(l => l.action.startsWith('ANALYSIS_'));
        const propertyLogs = logs.filter(l => l.action.startsWith('PROPERTY_'));
        const reportLogs = logs.filter(l => l.action.startsWith('REPORT_'));

        return {
            userId,
            period: {
                start: startDate.toISOString(),
                end: endDate.toISOString(),
            },
            summary: {
                totalEvents: logs.length,
                analyses: analysisLogs.length,
                properties: propertyLogs.length,
                reports: reportLogs.length,
            },
            logs,
        };
    }

    // ==========================================
    // EVENT HANDLERS
    // ==========================================

    @OnEvent('analysis.started')
    async handleAnalysisStarted(payload: any): Promise<void> {
        if (payload.userId) {
            await this.logAnalysisEvent(
                payload.userId,
                AuditAction.ANALYSIS_STARTED,
                payload.analysisId || payload.jobId,
                { buildingType: payload.buildingType },
            );
        }
    }

    @OnEvent('analysis.completed')
    async handleAnalysisCompleted(payload: any): Promise<void> {
        if (payload.userId) {
            await this.logAnalysisEvent(
                payload.userId,
                AuditAction.ANALYSIS_COMPLETED,
                payload.analysisId || payload.jobId,
                {
                    energyLabel: payload.energyLabel,
                    detections: payload.detections,
                    durationMs: payload.durationMs,
                },
            );
        }
    }

    @OnEvent('analysis.failed')
    async handleAnalysisFailed(payload: any): Promise<void> {
        if (payload.userId) {
            await this.logAnalysisEvent(
                payload.userId,
                AuditAction.ANALYSIS_FAILED,
                payload.analysisId || payload.jobId,
                { error: payload.error },
            );
        }
    }

    @OnEvent('report.generated')
    async handleReportGenerated(payload: any): Promise<void> {
        if (payload.userId) {
            await this.logReportEvent(
                payload.userId,
                AuditAction.REPORT_GENERATED,
                payload.reportId,
                { format: payload.format, analysisId: payload.analysisId },
            );
        }
    }

    @OnEvent('property.created')
    async handlePropertyCreated(payload: any): Promise<void> {
        if (payload.userId) {
            await this.logPropertyEvent(
                payload.userId,
                AuditAction.PROPERTY_CREATED,
                payload.propertyId,
                { title: payload.title, address: payload.address },
            );
        }
    }
}
