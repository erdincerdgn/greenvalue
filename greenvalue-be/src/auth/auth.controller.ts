import {
    Body,
    Controller,
    Get,
    Post,
    Put,
    UseGuards,
    Request,
    HttpCode,
    HttpStatus,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiBearerAuth, ApiBody } from '@nestjs/swagger';

import { RegisterDto, CompleteProfileDto } from './dto/register.dto';
import { LoginDto, ChangePasswordDto, ForgotPasswordDto, ResetPasswordDto } from './dto/login.dto';
import { AuthResponseDto } from './dto/auth.response.dto';
import { CurrentUserDto } from './dto/user.dto';
import { JwtAuthGuard } from './guards/jwt-auth.guard';
import { AdminAuthGuard } from './guards/admin-auth.guard';
import { AuthService } from './auth.service';

@ApiTags('Auth')
@Controller('auth')
export class AuthController {
    constructor(private readonly authService: AuthService) {}

    @Post('register')
    @HttpCode(HttpStatus.CREATED)
    @ApiOperation({ summary: 'Register a new user account' })
    @ApiResponse({ status: 201, description: 'User registered successfully', type: AuthResponseDto })
    @ApiResponse({ status: 409, description: 'Email already exists' })
    @ApiBody({ type: RegisterDto })
    async register(@Body() dto: RegisterDto): Promise<AuthResponseDto> {
        return this.authService.register(dto);
    }

    @Post('login')
    @HttpCode(HttpStatus.OK)
    @ApiOperation({ summary: 'Login for property owners / contractors' })
    @ApiResponse({ status: 200, description: 'Login successful', type: AuthResponseDto })
    @ApiResponse({ status: 401, description: 'Invalid credentials' })
    @ApiBody({ type: LoginDto })
    async login(@Body() dto: LoginDto): Promise<AuthResponseDto> {
        return this.authService.loginFrontend(dto);
    }

    @Post('login-admin')
    @HttpCode(HttpStatus.OK)
    @ApiOperation({ summary: 'Login for admin panel' })
    @ApiResponse({ status: 200, description: 'Admin login successful', type: AuthResponseDto })
    @ApiResponse({ status: 401, description: 'Invalid credentials or unauthorized role' })
    @ApiBody({ type: LoginDto })
    async loginAdmin(@Body() dto: LoginDto): Promise<AuthResponseDto> {
        return this.authService.loginAdmin(dto);
    }

    @Post('forgot-password')
    @HttpCode(HttpStatus.OK)
    @ApiOperation({ summary: 'Request password reset email' })
    @ApiResponse({ status: 200, description: 'Reset email sent if account exists' })
    @ApiBody({ type: ForgotPasswordDto })
    async forgotPassword(@Body() dto: ForgotPasswordDto) {
        return this.authService.forgotPassword(dto);
    }

    @Post('reset-password')
    @HttpCode(HttpStatus.OK)
    @ApiOperation({ summary: 'Reset password with token' })
    @ApiResponse({ status: 200, description: 'Password reset successful' })
    @ApiBody({ type: ResetPasswordDto })
    async resetPassword(@Body() dto: ResetPasswordDto) {
        return this.authService.resetPassword(dto);
    }

    @Get('me')
    @UseGuards(JwtAuthGuard)
    @ApiBearerAuth('JWT')
    @ApiOperation({ summary: 'Get current user profile' })
    @ApiResponse({ status: 200, description: 'Current user data', type: CurrentUserDto })
    async getCurrentUser(@Request() req): Promise<CurrentUserDto> {
        return this.authService.getCurrentUser(req.user.id);
    }

    @Put('profile')
    @UseGuards(JwtAuthGuard)
    @ApiBearerAuth('JWT')
    @ApiOperation({ summary: 'Update user profile' })
    @ApiResponse({ status: 200, description: 'Profile updated successfully' })
    @ApiBody({ type: CompleteProfileDto })
    async updateProfile(@Request() req, @Body() dto: CompleteProfileDto) {
        return this.authService.updateProfile(req.user.id, dto);
    }

    @Post('change-password')
    @UseGuards(JwtAuthGuard)
    @HttpCode(HttpStatus.OK)
    @ApiBearerAuth('JWT')
    @ApiOperation({ summary: 'Change password' })
    @ApiResponse({ status: 200, description: 'Password changed successfully' })
    @ApiBody({ type: ChangePasswordDto })
    async changePassword(@Request() req, @Body() dto: ChangePasswordDto) {
        return this.authService.changePassword(req.user.id, dto);
    }

    @Get('admin/users/me')
    @UseGuards(AdminAuthGuard)
    @ApiBearerAuth('JWT')
    @ApiOperation({ summary: 'Get admin user profile' })
    @ApiResponse({ status: 200, description: 'Admin user data' })
    async getAdminUser(@Request() req): Promise<CurrentUserDto> {
        return this.authService.getCurrentUser(req.user.id);
    }
}
