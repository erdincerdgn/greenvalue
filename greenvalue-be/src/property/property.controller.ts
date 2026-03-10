import {
    Controller,
    Get,
    Post,
    Patch,
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
import { PropertyService } from './property.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { AdminAuthGuard } from '../auth/guards/admin-auth.guard';
import { CurrentUser } from '../common/decorators/roles.decorator';
import { CreatePropertyDto, UpdatePropertyDto, PropertyListQueryDto, PropertyResponseDto, UploadUrlDto, UploadUrlResponseDto } from './dto';
import { Role } from '@prisma/client';
import { StorageService } from '../core/storage/storage.service';
import { randomUUID } from 'crypto';

@ApiTags('Properties')
@Controller('properties')
@UseGuards(JwtAuthGuard)
@ApiBearerAuth()
export class PropertyController {
    constructor(
        private readonly propertyService: PropertyService,
        private readonly storageService: StorageService,
    ) {}

    @Post()
    @HttpCode(HttpStatus.CREATED)
    @ApiOperation({ summary: 'Create a new property' })
    @ApiResponse({ status: 201, type: PropertyResponseDto })
    async create(
        @CurrentUser('id') userId: string,
        @Body() dto: CreatePropertyDto,
    ) {
        return this.propertyService.create(userId, dto);
    }

    @Get()
    @ApiOperation({ summary: 'List my properties' })
    async findMyProperties(
        @CurrentUser('id') userId: string,
        @Query() query: PropertyListQueryDto,
    ) {
        return this.propertyService.findAllByUser(userId, query);
    }

    @Get('admin/all')
    @UseGuards(AdminAuthGuard)
    @ApiOperation({ summary: 'List all properties (admin)' })
    async findAll(@Query() query: PropertyListQueryDto) {
        return this.propertyService.findAll(query);
    }

    @Get(':id')
    @ApiOperation({ summary: 'Get property details' })
    @ApiParam({ name: 'id', type: String })
    async findOne(
        @Param('id', ParseUUIDPipe) id: string,
        @CurrentUser('id') userId: string,
        @CurrentUser('role') role: Role,
    ) {
        return this.propertyService.findOne(id, userId, role);
    }

    @Patch(':id')
    @ApiOperation({ summary: 'Update a property' })
    @ApiParam({ name: 'id', type: String })
    async update(
        @Param('id', ParseUUIDPipe) id: string,
        @CurrentUser('id') userId: string,
        @CurrentUser('role') role: Role,
        @Body() dto: UpdatePropertyDto,
    ) {
        return this.propertyService.update(id, userId, role, dto);
    }

    @Post(':id/upload-url')
    @HttpCode(HttpStatus.OK)
    @ApiOperation({ summary: 'Get pre-signed upload URL for a property photo' })
    @ApiParam({ name: 'id', type: String })
    @ApiResponse({ status: 200, type: UploadUrlResponseDto })
    async getUploadUrl(
        @Param('id', ParseUUIDPipe) id: string,
        @CurrentUser('id') userId: string,
        @CurrentUser('role') role: Role,
        @Body() dto: UploadUrlDto,
    ): Promise<UploadUrlResponseDto> {
        // Verify ownership / access
        await this.propertyService.findOne(id, userId, role);

        // Build a unique object key: properties/<propertyId>/<uuid>-<fileName>
        const ext = dto.fileName.split('.').pop() || 'jpg';
        const fileKey = `properties/${id}/${randomUUID()}.${ext}`;

        const uploadUrl = await this.storageService.getPresignedUploadUrl(
            StorageService.BUCKETS.RAW_UPLOADS,
            fileKey,
            3600, // 1 hour expiry
        );

        return { uploadUrl, fileKey };
    }

    @Delete(':id')
    @HttpCode(HttpStatus.OK)
    @ApiOperation({ summary: 'Delete a property' })
    @ApiParam({ name: 'id', type: String })
    async remove(
        @Param('id', ParseUUIDPipe) id: string,
        @CurrentUser('id') userId: string,
        @CurrentUser('role') role: Role,
    ) {
        return this.propertyService.remove(id, userId, role);
    }
}
