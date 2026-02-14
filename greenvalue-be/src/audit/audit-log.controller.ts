import { Controller, Get, Query, Param, UseGuards, ParseUUIDPipe } from '@nestjs/common';
import { ApiTags, ApiBearerAuth, ApiOperation, ApiParam } from '@nestjs/swagger';
import { AuditLogService, AuditAction } from './audit-log.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { AdminAuthGuard } from '../auth/guards/admin-auth.guard';
import { CurrentUser } from '../common/decorators/roles.decorator';

/**
 * Audit Log Controller for GreenValue AI Platform
 */
@ApiTags('Audit')
@Controller('api/v1/audit')
@UseGuards(JwtAuthGuard)
export class AuditLogController {
    constructor(private readonly auditService: AuditLogService) {}

    /**
     * Get current user's audit history
     */
    @Get('my-history')
    @ApiBearerAuth()
    @ApiOperation({ summary: 'Get my audit history' })
    async getMyHistory(
        @CurrentUser('id') userId: string,
        @Query('action') action?: string,
        @Query('entity') entity?: string,
        @Query('days') days: string = '30',
        @Query('limit') limit: string = '100',
    ) {
        const startDate = new Date(Date.now() - parseInt(days) * 24 * 60 * 60 * 1000);

        const logs = await this.auditService.getUserAuditHistory(userId, {
            action: action as AuditAction,
            entity,
            startDate,
            limit: parseInt(limit),
        });

        return { userId, count: logs.length, logs };
    }

    /**
     * Get user's audit history (admin only)
     */
    @Get('history/:userId')
    @UseGuards(AdminAuthGuard)
    @ApiBearerAuth()
    @ApiOperation({ summary: 'Get user audit history (admin)' })
    @ApiParam({ name: 'userId', type: String })
    async getHistory(
        @Param('userId', ParseUUIDPipe) userId: string,
        @Query('action') action?: string,
        @Query('entity') entity?: string,
        @Query('days') days: string = '30',
        @Query('limit') limit: string = '100',
    ) {
        const startDate = new Date(Date.now() - parseInt(days) * 24 * 60 * 60 * 1000);

        const logs = await this.auditService.getUserAuditHistory(userId, {
            action: action as AuditAction,
            entity,
            startDate,
            limit: parseInt(limit),
        });

        return { userId, count: logs.length, logs };
    }

    /**
     * Export audit logs (admin only)
     */
    @Get('export/:userId')
    @UseGuards(AdminAuthGuard)
    @ApiBearerAuth()
    @ApiOperation({ summary: 'Export audit logs (admin)' })
    @ApiParam({ name: 'userId', type: String })
    async exportLogs(
        @Param('userId', ParseUUIDPipe) userId: string,
        @Query('startDate') startDate?: string,
        @Query('endDate') endDate?: string,
    ) {
        const start = startDate ? new Date(startDate) : new Date(Date.now() - 90 * 24 * 60 * 60 * 1000);
        const end = endDate ? new Date(endDate) : new Date();

        return this.auditService.exportAuditLogs(userId, start, end);
    }
}
