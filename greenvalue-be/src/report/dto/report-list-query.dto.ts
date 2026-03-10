import { IsEnum, IsOptional, IsInt, Min, Max, IsString } from 'class-validator';
import { ApiPropertyOptional } from '@nestjs/swagger';
import { Transform } from 'class-transformer';
import { ReportFormat } from '@prisma/client';
import { ReportType } from './generate-report.dto';

export class ReportListQueryDto {
    @ApiPropertyOptional({ description: 'Page number', default: 1 })
    @IsOptional()
    @Transform(({ value }) => parseInt(value, 10))
    @IsInt()
    @Min(1)
    page?: number = 1;

    @ApiPropertyOptional({ description: 'Items per page', default: 20 })
    @IsOptional()
    @Transform(({ value }) => parseInt(value, 10))
    @IsInt()
    @Min(1)
    @Max(100)
    limit?: number = 20;

    @ApiPropertyOptional({ enum: ReportFormat })
    @IsOptional()
    @IsEnum(ReportFormat)
    format?: ReportFormat;

    @ApiPropertyOptional({ enum: ReportType })
    @IsOptional()
    @IsEnum(ReportType)
    reportType?: ReportType;

    @ApiPropertyOptional({ description: 'Filter by property ID' })
    @IsOptional()
    @IsString()
    propertyId?: string;
}
