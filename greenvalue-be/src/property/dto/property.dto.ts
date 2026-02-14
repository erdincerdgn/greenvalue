import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsString, IsOptional, IsNumber, Min, Max } from 'class-validator';
import { Type } from 'class-transformer';

export class CreatePropertyDto {
    @ApiProperty({ example: 'Riverside Apartment Block A' })
    @IsString()
    title: string;

    @ApiProperty({ example: 'Keizersgracht 123' })
    @IsString()
    address: string;

    @ApiProperty({ example: 'Amsterdam' })
    @IsString()
    city: string;

    @ApiPropertyOptional({ example: 'Centrum' })
    @IsOptional()
    @IsString()
    district?: string;

    @ApiPropertyOptional({ example: 1985 })
    @IsOptional()
    @Type(() => Number)
    @IsNumber()
    @Min(1800)
    @Max(2030)
    buildingYear?: number;

    @ApiPropertyOptional({ example: 'apartment' })
    @IsOptional()
    @IsString()
    buildingType?: string;

    @ApiPropertyOptional({ example: 120.5 })
    @IsOptional()
    @Type(() => Number)
    @IsNumber()
    @Min(1)
    floorArea?: number;

    @ApiPropertyOptional({ description: 'MinIO key for thumbnail image' })
    @IsOptional()
    @IsString()
    thumbnailKey?: string;
}

export class UpdatePropertyDto {
    @ApiPropertyOptional()
    @IsOptional()
    @IsString()
    title?: string;

    @ApiPropertyOptional()
    @IsOptional()
    @IsString()
    address?: string;

    @ApiPropertyOptional()
    @IsOptional()
    @IsString()
    city?: string;

    @ApiPropertyOptional()
    @IsOptional()
    @IsString()
    district?: string;

    @ApiPropertyOptional()
    @IsOptional()
    @Type(() => Number)
    @IsNumber()
    @Min(1800)
    @Max(2030)
    buildingYear?: number;

    @ApiPropertyOptional()
    @IsOptional()
    @IsString()
    buildingType?: string;

    @ApiPropertyOptional()
    @IsOptional()
    @Type(() => Number)
    @IsNumber()
    @Min(1)
    floorArea?: number;

    @ApiPropertyOptional()
    @IsOptional()
    @IsString()
    thumbnailKey?: string;
}

export class PropertyResponseDto {
    @ApiProperty() id: string;
    @ApiProperty() title: string;
    @ApiProperty() address: string;
    @ApiProperty() city: string;
    @ApiPropertyOptional() district?: string;
    @ApiPropertyOptional() buildingYear?: number;
    @ApiPropertyOptional() buildingType?: string;
    @ApiPropertyOptional() floorArea?: number;
    @ApiPropertyOptional() thumbnailKey?: string;
    @ApiProperty() ownerId: string;
    @ApiProperty() createdAt: Date;
    @ApiProperty() updatedAt: Date;
    @ApiPropertyOptional() analysisCount?: number;
}

export class PropertyListQueryDto {
    @ApiPropertyOptional({ default: 1 })
    @IsOptional()
    @Type(() => Number)
    @IsNumber()
    @Min(1)
    page?: number;

    @ApiPropertyOptional({ default: 10 })
    @IsOptional()
    @Type(() => Number)
    @IsNumber()
    @Min(1)
    @Max(100)
    limit?: number;

    @ApiPropertyOptional()
    @IsOptional()
    @IsString()
    search?: string;

    @ApiPropertyOptional()
    @IsOptional()
    @IsString()
    city?: string;

    @ApiPropertyOptional()
    @IsOptional()
    @IsString()
    buildingType?: string;

    @ApiPropertyOptional({ enum: ['createdAt', 'title', 'city', 'buildingYear'], default: 'createdAt' })
    @IsOptional()
    @IsString()
    sortBy?: string;

    @ApiPropertyOptional({ enum: ['asc', 'desc'], default: 'desc' })
    @IsOptional()
    @IsString()
    sortDirection?: 'asc' | 'desc';
}
