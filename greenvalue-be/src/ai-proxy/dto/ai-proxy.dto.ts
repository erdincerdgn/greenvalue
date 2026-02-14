import {
    IsString,
    IsOptional,
    IsNumber,
    IsUUID,
    Min,
    Max,
    IsArray,
} from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

// ============================================================
// ENUMS (Matching GreenValue Proto)
// ============================================================

export enum AnalysisStatusDto {
    PENDING = 'PENDING',
    PROCESSING = 'PROCESSING',
    COMPLETED = 'COMPLETED',
    FAILED = 'FAILED',
}

export enum EnergyLabelDto {
    A_PLUS = 'A_PLUS',
    A = 'A',
    B = 'B',
    C = 'C',
    D = 'D',
    E = 'E',
    F = 'F',
    G = 'G',
}

// ============================================================
// IMAGE ANALYSIS DTOs
// ============================================================

export class AnalyzeImageDto {
    @ApiProperty({ description: 'MinIO object key for the uploaded image' })
    @IsString()
    imageKey: string;

    @ApiProperty({ description: 'Property ID this analysis belongs to' })
    @IsUUID()
    propertyId: string;

    @ApiPropertyOptional({ description: 'Building type hint', example: 'apartment' })
    @IsOptional()
    @IsString()
    buildingType?: string;

    @ApiPropertyOptional({ description: 'Building year for age-based adjustments' })
    @IsOptional()
    @IsNumber()
    buildingYear?: number;

    @ApiPropertyOptional({ description: 'YOLO confidence threshold (0-1)', default: 0.25 })
    @IsOptional()
    @IsNumber()
    @Min(0.1)
    @Max(0.9)
    confidenceThreshold?: number;
}

export class AnalyzeImageUploadDto {
    @ApiProperty({ description: 'Property ID this analysis belongs to' })
    @IsUUID()
    propertyId: string;

    @ApiPropertyOptional({ description: 'Building type hint', example: 'apartment' })
    @IsOptional()
    @IsString()
    buildingType?: string;

    @ApiPropertyOptional({ description: 'Building year' })
    @IsOptional()
    @IsNumber()
    buildingYear?: number;
}

export class DetectionDto {
    @ApiProperty({ description: 'Detected component type (window, door, facade, roof, etc.)' })
    className: string;

    @ApiProperty({ description: 'Detection confidence (0-1)' })
    confidence: number;

    @ApiProperty({ description: 'Bounding box [x1, y1, x2, y2]' })
    bbox: number[];
}

export class ComponentUValueDto {
    @ApiProperty({ description: 'Component name (e.g., single_glazed_window)' })
    name: string;

    @ApiProperty({ description: 'U-Value in W/(m²·K)' })
    uValue: number;

    @ApiProperty({ description: 'Component area in m²' })
    area: number;

    @ApiPropertyOptional()
    layers?: string[];
}

export class RenovationSuggestionDto {
    @ApiProperty({ description: 'Component to renovate' })
    component: string;

    @ApiProperty({ description: 'Current U-Value' })
    currentUValue: number;

    @ApiProperty({ description: 'Improved U-Value after renovation' })
    improvedUValue: number;

    @ApiProperty({ description: 'Estimated cost in EUR' })
    estimatedCost: number;

    @ApiProperty({ description: 'Annual energy savings in EUR' })
    annualSavings: number;

    @ApiProperty({ description: 'Payback period in years' })
    paybackYears: number;

    @ApiProperty({ description: 'CO₂ reduction in kg/year' })
    co2ReductionKg: number;
}

export class AnalysisResultDto {
    @ApiProperty()
    jobId: string;

    @ApiProperty({ type: [DetectionDto] })
    detections: DetectionDto[];

    @ApiPropertyOptional()
    overallUValue?: number;

    @ApiPropertyOptional({ enum: EnergyLabelDto })
    energyLabel?: EnergyLabelDto;

    @ApiPropertyOptional({ type: [ComponentUValueDto] })
    components?: ComponentUValueDto[];

    @ApiPropertyOptional({ type: [RenovationSuggestionDto] })
    renovations?: RenovationSuggestionDto[];

    @ApiPropertyOptional({ description: 'MinIO key for heatmap overlay image' })
    heatmapKey?: string;

    @ApiPropertyOptional()
    modelVersion?: string;

    @ApiPropertyOptional()
    inferenceTimeMs?: number;

    @ApiPropertyOptional()
    pipelineTimeMs?: number;
}

export class AnalysisStatusResponseDto {
    @ApiProperty()
    jobId: string;

    @ApiProperty({ enum: AnalysisStatusDto })
    status: AnalysisStatusDto;

    @ApiPropertyOptional()
    progress?: number;

    @ApiPropertyOptional()
    result?: AnalysisResultDto;

    @ApiPropertyOptional()
    errorMessage?: string;
}

// ============================================================
// U-VALUE CALCULATION DTOs
// ============================================================

export class CalculateUValueDto {
    @ApiProperty({
        description: 'Array of material layer names',
        example: ['brick_solid', 'mineral_wool_50mm', 'plasterboard'],
    })
    @IsArray()
    @IsString({ each: true })
    layers: string[];

    @ApiPropertyOptional({
        description: 'Custom thicknesses per layer (mm)',
        example: [240, 50, 12.5],
    })
    @IsOptional()
    @IsArray()
    @IsNumber({}, { each: true })
    thicknesses?: number[];

    @ApiPropertyOptional({ description: 'Building year for age adjustment' })
    @IsOptional()
    @IsNumber()
    buildingYear?: number;
}

export class UValueResultDto {
    @ApiProperty({ description: 'Calculated U-Value in W/(m²·K)' })
    uValue: number;

    @ApiProperty({ enum: EnergyLabelDto })
    energyLabel: EnergyLabelDto;

    @ApiProperty({ description: 'Total thermal resistance in m²·K/W' })
    totalResistance: number;

    @ApiProperty({ description: 'Layer breakdown' })
    layers: Array<{
        material: string;
        thickness: number;
        conductivity: number;
        resistance: number;
    }>;
}

// ============================================================
// SIMILAR PROPERTIES DTOs
// ============================================================

export class FindSimilarDto {
    @ApiProperty({ description: 'Property ID to find similar ones for' })
    @IsUUID()
    propertyId: string;

    @ApiPropertyOptional({ description: 'Maximum number of results', default: 5 })
    @IsOptional()
    @IsNumber()
    @Min(1)
    @Max(20)
    limit?: number;

    @ApiPropertyOptional({ description: 'Minimum similarity score (0-1)', default: 0.7 })
    @IsOptional()
    @IsNumber()
    @Min(0)
    @Max(1)
    minScore?: number;
}

export class SimilarPropertyDto {
    @ApiProperty()
    propertyId: string;

    @ApiProperty()
    similarityScore: number;

    @ApiPropertyOptional()
    address?: string;

    @ApiPropertyOptional()
    energyLabel?: string;

    @ApiPropertyOptional()
    overallUValue?: number;
}

// ============================================================
// REPORT GENERATION DTOs
// ============================================================

export class GenerateReportDto {
    @ApiProperty({ description: 'Analysis ID to generate report for' })
    @IsUUID()
    analysisId: string;

    @ApiPropertyOptional({ enum: ['PDF', 'JSON'], default: 'PDF' })
    @IsOptional()
    @IsString()
    format?: 'PDF' | 'JSON';

    @ApiPropertyOptional({ description: 'Include renovation ROI analysis', default: true })
    @IsOptional()
    includeRenovations?: boolean;
}

export class ReportResponseDto {
    @ApiProperty()
    reportId: string;

    @ApiProperty({ description: 'MinIO key for the generated report' })
    fileKey: string;

    @ApiPropertyOptional()
    fileSize?: number;

    @ApiProperty()
    format: string;
}

// ============================================================
// HEALTH & MONITORING DTOs
// ============================================================

export class AIHealthResponseDto {
    @ApiProperty()
    status: string;

    @ApiProperty()
    modelLoaded: boolean;

    @ApiPropertyOptional()
    modelVersion?: string;

    @ApiPropertyOptional()
    device?: string;

    @ApiPropertyOptional()
    gpuAvailable?: boolean;

    @ApiPropertyOptional()
    totalAnalyses?: number;
}
