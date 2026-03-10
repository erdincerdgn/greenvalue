import { IsEnum, IsOptional, IsString, IsUUID } from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { ReportFormat } from '@prisma/client';

/**
 * Local enum — mirrors prisma ReportType.
 * Remove after `npx prisma migrate dev && npx prisma generate`
 * and import from '@prisma/client' instead.
 */
export enum ReportType {
    ENERGY_CERTIFICATE = 'ENERGY_CERTIFICATE',
    ROI_ANALYSIS = 'ROI_ANALYSIS',
    COMPARISON = 'COMPARISON',
    FULL_IVS = 'FULL_IVS',
}

export class GenerateReportDto {
    @ApiProperty({ description: 'Analysis UUID to generate report from' })
    @IsUUID()
    analysisId: string;

    @ApiPropertyOptional({ enum: ReportFormat, default: 'PDF' })
    @IsOptional()
    @IsEnum(ReportFormat)
    format?: ReportFormat = ReportFormat.PDF;

    @ApiPropertyOptional({ enum: ReportType, default: 'FULL_IVS' })
    @IsOptional()
    @IsEnum(ReportType)
    reportType?: ReportType = ReportType.FULL_IVS;

    @ApiPropertyOptional({ description: 'Report language: en, tr, de', default: 'en' })
    @IsOptional()
    @IsString()
    language?: string = 'en';
}
