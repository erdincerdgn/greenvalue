import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { ReportFormat } from '@prisma/client';
import { ReportType } from './generate-report.dto';

export class ReportResponseDto {
    @ApiProperty()
    id: string;

    @ApiProperty({ enum: ReportFormat })
    format: ReportFormat;

    @ApiProperty({ enum: ReportType })
    reportType: ReportType;

    @ApiPropertyOptional()
    title?: string;

    @ApiProperty()
    fileKey: string;

    @ApiPropertyOptional()
    fileSize?: number;

    @ApiPropertyOptional()
    language?: string;

    @ApiPropertyOptional()
    generationTimeMs?: number;

    @ApiProperty()
    analysisId: string;

    @ApiProperty()
    propertyId: string;

    @ApiProperty()
    userId: string;

    @ApiProperty()
    createdAt: Date;

    @ApiPropertyOptional({ description: 'Pre-signed download URL (included on detail requests)' })
    downloadUrl?: string;
}
