import {
    Injectable,
    UnauthorizedException,
    ConflictException,
    ForbiddenException,
    BadRequestException,
    Logger,
} from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { PrismaService } from '../core/prisma/prisma.service';
import { RegisterDto, CompleteProfileDto } from './dto/register.dto';
import { LoginDto, ChangePasswordDto, ForgotPasswordDto, ResetPasswordDto } from './dto/login.dto';
import { AuthResponseDto, UserResponseDto } from './dto/auth.response.dto';
import { CurrentUserDto } from './dto/user.dto';
import * as bcrypt from 'bcrypt';
import { Role, User } from '@prisma/client';

@Injectable()
export class AuthService {
    private readonly logger = new Logger(AuthService.name);

    constructor(
        private prisma: PrismaService,
        private jwtService: JwtService,
    ) {}

    // ==========================================
    // REGISTER
    // ==========================================

    async register(dto: RegisterDto): Promise<AuthResponseDto> {
        const existingUser = await this.prisma.user.findUnique({
            where: { email: dto.email },
        });

        if (existingUser) {
            throw new ConflictException('Email already exists');
        }

        const hashedPassword = await bcrypt.hash(dto.password, 12);

        const user = await this.prisma.user.create({
            data: {
                email: dto.email,
                fullName: dto.fullName,
                phone: dto.phone,
                password: hashedPassword,
                role: dto.role || Role.OWNER,
                isActive: true,
            },
        });

        this.logger.log(`New user registered: ${user.email}`);

        const token = this.generateToken(user.id, user.email, user.role, 'frontend');

        return {
            accessToken: token,
            expiresIn: 30 * 24 * 60 * 60,
            user: this.mapUserToResponse(user),
        };
    }

    // ==========================================
    // LOGIN
    // ==========================================

    private async authenticate(dto: LoginDto): Promise<User> {
        const user = await this.prisma.user.findUnique({
            where: { email: dto.email },
        });

        if (!user) {
            this.logger.warn(`Login attempt with non-existent email: ${dto.email}`);
            throw new UnauthorizedException('Invalid credentials');
        }

        if (!user.isActive) {
            throw new ForbiddenException('Your account is inactive. Please contact support.');
        }

        const isPasswordValid = await bcrypt.compare(dto.password, user.password);

        if (!isPasswordValid) {
            this.logger.warn(`Failed login attempt for: ${dto.email}`);
            throw new UnauthorizedException('Invalid credentials');
        }

        await this.prisma.user.update({
            where: { id: user.id },
            data: { lastLogin: new Date() },
        });

        return user;
    }

    async loginFrontend(dto: LoginDto): Promise<AuthResponseDto> {
        const user = await this.authenticate(dto);

        if (user.role === Role.ADMIN) {
            throw new UnauthorizedException('Please use admin panel for admin accounts');
        }

        const token = this.generateToken(user.id, user.email, user.role, 'frontend');

        this.logger.log(`Frontend login: ${user.email}`);

        return {
            accessToken: token,
            expiresIn: 30 * 24 * 60 * 60,
            user: this.mapUserToResponse(user),
        };
    }

    async loginAdmin(dto: LoginDto): Promise<AuthResponseDto> {
        const user = await this.authenticate(dto);

        if (user.role !== Role.ADMIN) {
            this.logger.warn(`Admin login attempt by non-admin user: ${user.email}`);
            throw new UnauthorizedException('Admin access restricted to authorized accounts only');
        }

        const token = this.generateToken(user.id, user.email, user.role, 'admin');

        this.logger.log(`Admin login: ${user.email} (${user.role})`);

        return {
            accessToken: token,
            expiresIn: 24 * 60 * 60,
            user: this.mapUserToResponse(user),
        };
    }

    // ==========================================
    // USER INFO
    // ==========================================

    async validateUser(userId: string): Promise<User | null> {
        return this.prisma.user.findUnique({
            where: { id: userId },
        });
    }

    async getCurrentUser(userId: string): Promise<CurrentUserDto> {
        const user = await this.prisma.user.findUnique({
            where: { id: userId },
            include: {
                _count: {
                    select: {
                        properties: true,
                        analyses: true,
                    },
                },
            },
        });

        if (!user) {
            throw new UnauthorizedException('User not found');
        }

        return {
            id: user.id,
            email: user.email,
            fullName: user.fullName,
            phone: user.phone,
            avatar: user.avatar,
            role: user.role,
            isActive: user.isActive,
            lastLogin: user.lastLogin,
            createdAt: user.createdAt,
            propertyCount: user._count.properties,
            analysisCount: user._count.analyses,
        };
    }

    // ==========================================
    // PROFILE UPDATE
    // ==========================================

    async updateProfile(userId: string, dto: CompleteProfileDto): Promise<UserResponseDto> {
        const updateData: any = {};

        if (dto.fullName !== undefined) updateData.fullName = dto.fullName;
        if (dto.phone !== undefined) updateData.phone = dto.phone;
        if (dto.avatar !== undefined) updateData.avatar = dto.avatar;

        const user = await this.prisma.user.update({
            where: { id: userId },
            data: updateData,
        });

        return this.mapUserToResponse(user);
    }

    // ==========================================
    // PASSWORD MANAGEMENT
    // ==========================================

    async changePassword(userId: string, dto: ChangePasswordDto): Promise<{ message: string }> {
        if (dto.newPassword !== dto.confirmPassword) {
            throw new BadRequestException('Passwords do not match');
        }

        const user = await this.prisma.user.findUnique({
            where: { id: userId },
        });

        if (!user) {
            throw new UnauthorizedException('User not found');
        }

        const isCurrentValid = await bcrypt.compare(dto.currentPassword, user.password);
        if (!isCurrentValid) {
            throw new UnauthorizedException('Current password is incorrect');
        }

        const hashedPassword = await bcrypt.hash(dto.newPassword, 12);

        await this.prisma.user.update({
            where: { id: userId },
            data: { password: hashedPassword },
        });

        this.logger.log(`Password changed for user ${userId}`);

        return { message: 'Password changed successfully' };
    }

    async forgotPassword(dto: ForgotPasswordDto): Promise<{ message: string }> {
        const user = await this.prisma.user.findUnique({
            where: { email: dto.email },
        });

        if (!user || !user.isActive) {
            return { message: 'If an account exists with this email, you will receive a password reset link.' };
        }

        // Generate reset token (TODO: Send via email)
        this.jwtService.sign(
            { sub: user.id, email: user.email, type: 'password_reset' },
            { expiresIn: '1h' },
        );

        this.logger.log(`Password reset token generated for user: ${user.email}`);
        // TODO: Send email with reset token

        return { message: 'If an account exists with this email, you will receive a password reset link.' };
    }

    async resetPassword(dto: ResetPasswordDto): Promise<{ message: string }> {
        if (dto.newPassword !== dto.confirmPassword) {
            throw new BadRequestException('Passwords do not match');
        }

        try {
            const payload = this.jwtService.verify(dto.token);

            if (payload.type !== 'password_reset') {
                throw new BadRequestException('Invalid reset token');
            }

            const user = await this.prisma.user.findUnique({
                where: { id: payload.sub },
            });

            if (!user || user.email !== payload.email) {
                throw new BadRequestException('Invalid reset token');
            }

            const hashedPassword = await bcrypt.hash(dto.newPassword, 12);

            await this.prisma.user.update({
                where: { id: user.id },
                data: { password: hashedPassword },
            });

            this.logger.log(`Password reset successful for user: ${user.email}`);

            return { message: 'Password has been reset successfully.' };
        } catch (error) {
            if (error.name === 'TokenExpiredError') {
                throw new BadRequestException('Reset token has expired.');
            }
            if (error instanceof BadRequestException) throw error;
            throw new BadRequestException('Invalid reset token');
        }
    }

    // ==========================================
    // OAUTH
    // ==========================================

    async findOrCreateOAuthUser(data: {
        provider: string;
        providerId: string;
        email?: string;
        firstName?: string;
        lastName?: string;
        picture?: string;
    }): Promise<User> {
        if (data.email) {
            const existingUser = await this.prisma.user.findUnique({
                where: { email: data.email },
            });

            if (existingUser) {
                const user = await this.prisma.user.update({
                    where: { id: existingUser.id },
                    data: {
                        lastLogin: new Date(),
                        avatar: data.picture || existingUser.avatar,
                    },
                });
                this.logger.log(`OAuth login: ${user.email} (${data.provider})`);
                return user;
            }
        }

        const fullName = [data.firstName, data.lastName].filter(Boolean).join(' ') || 'User';

        const user = await this.prisma.user.create({
            data: {
                email: data.email || `${data.providerId}@${data.provider}.oauth`,
                fullName,
                password: require('uuid').v4(),
                role: Role.OWNER,
                isActive: true,
                avatar: data.picture,
            },
        });

        this.logger.log(`New OAuth user created: ${user.email} (${data.provider})`);
        return user;
    }

    async generateTokens(user: User): Promise<{ accessToken: string; refreshToken: string }> {
        const accessToken = this.generateToken(user.id, user.email, user.role, 'frontend');
        const refreshToken = this.jwtService.sign(
            { sub: user.id, type: 'refresh' },
            { expiresIn: '30d' },
        );
        return { accessToken, refreshToken };
    }

    // ==========================================
    // HELPERS
    // ==========================================

    private generateToken(
        userId: string,
        email: string,
        role: Role,
        tokenType: 'frontend' | 'admin',
    ): string {
        return this.jwtService.sign({
            sub: userId,
            email,
            role,
            tokenType,
        });
    }

    private mapUserToResponse(user: User): UserResponseDto {
        return {
            id: user.id,
            email: user.email,
            fullName: user.fullName,
            phone: user.phone,
            avatar: user.avatar,
            role: user.role,
            isActive: user.isActive,
            lastLogin: user.lastLogin,
            createdAt: user.createdAt,
        };
    }
}
