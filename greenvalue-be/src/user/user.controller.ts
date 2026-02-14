import {
    Controller,
    Get,
    Patch,
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
import { UserService } from './user.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { AdminAuthGuard } from '../auth/guards/admin-auth.guard';
import { CurrentUser } from '../common/decorators/roles.decorator';
import { UpdateUserProfileDto, SearchUserDto, AdminUpdateUserDto, UserResponseDto, UserStatsDto } from './dto';

@ApiTags('Users')
@Controller('users')
export class UserController {
    constructor(private readonly userService: UserService) {}

    // ─── Current User Endpoints ──────────────────────────

    @Get('me')
    @UseGuards(JwtAuthGuard)
    @ApiBearerAuth()
    @ApiOperation({ summary: 'Get current user profile' })
    @ApiResponse({ status: 200, type: UserResponseDto })
    async getMe(@CurrentUser('id') userId: string) {
        return this.userService.findById(userId);
    }

    @Get('me/stats')
    @UseGuards(JwtAuthGuard)
    @ApiBearerAuth()
    @ApiOperation({ summary: 'Get current user statistics' })
    @ApiResponse({ status: 200, type: UserStatsDto })
    async getMyStats(@CurrentUser('id') userId: string) {
        return this.userService.getUserStats(userId);
    }

    @Patch('me/profile')
    @UseGuards(JwtAuthGuard)
    @ApiBearerAuth()
    @HttpCode(HttpStatus.OK)
    @ApiOperation({ summary: 'Update current user profile' })
    @ApiResponse({ status: 200, type: UserResponseDto })
    async updateMyProfile(
        @CurrentUser('id') userId: string,
        @Body() dto: UpdateUserProfileDto,
    ) {
        return this.userService.updateProfile(userId, dto);
    }

    // ─── Admin Endpoints ─────────────────────────────────

    @Get('admin/list')
    @UseGuards(JwtAuthGuard, AdminAuthGuard)
    @ApiBearerAuth()
    @ApiOperation({ summary: 'List all users (admin)' })
    async listUsers(@Query() query: SearchUserDto) {
        return this.userService.findAll(query);
    }

    @Get('admin/search')
    @UseGuards(JwtAuthGuard, AdminAuthGuard)
    @ApiBearerAuth()
    @ApiOperation({ summary: 'Search users (admin)' })
    async searchUsers(@Query() query: SearchUserDto) {
        return this.userService.searchUsers(query);
    }

    @Get('admin/:id')
    @UseGuards(JwtAuthGuard, AdminAuthGuard)
    @ApiBearerAuth()
    @ApiOperation({ summary: 'Get user by ID (admin)' })
    @ApiParam({ name: 'id', type: String })
    @ApiResponse({ status: 200, type: UserResponseDto })
    async getUserById(@Param('id', ParseUUIDPipe) id: string) {
        return this.userService.findById(id);
    }

    @Patch('admin/:id')
    @UseGuards(JwtAuthGuard, AdminAuthGuard)
    @ApiBearerAuth()
    @HttpCode(HttpStatus.OK)
    @ApiOperation({ summary: 'Update user (admin)' })
    @ApiParam({ name: 'id', type: String })
    @ApiResponse({ status: 200, type: UserResponseDto })
    async updateUser(
        @Param('id', ParseUUIDPipe) id: string,
        @Body() dto: AdminUpdateUserDto,
    ) {
        return this.userService.adminUpdateUser(id, dto);
    }
}
