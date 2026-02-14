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
import { CreatePropertyDto, UpdatePropertyDto, PropertyListQueryDto, PropertyResponseDto } from './dto';
import { Role } from '@prisma/client';

@ApiTags('Properties')
@Controller('api/v1/properties')
@UseGuards(JwtAuthGuard)
@ApiBearerAuth()
export class PropertyController {
    constructor(private readonly propertyService: PropertyService) {}

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
