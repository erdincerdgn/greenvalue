import { Injectable, NotFoundException, ConflictException } from '@nestjs/common';
import { PrismaService } from '../core/prisma/prisma.service';
import { RedisService } from '../core/redis/redis.service';
import { UpdateUserProfileDto, SearchUserDto, AdminUpdateUserDto, UserStatsDto } from './dto';
import { Prisma } from '@prisma/client';

const USER_SELECT = {
    id: true,
    email: true,
    fullName: true,
    phone: true,
    avatar: true,
    role: true,
    isActive: true,
    createdAt: true,
    updatedAt: true,
    lastLogin: true,
};

@Injectable()
export class UserService {
    constructor(
        private readonly prisma: PrismaService,
        private readonly redis: RedisService,
    ) {}

    // ─── Find By ID ──────────────────────────────────────

    async findById(id: string) {
        const cacheKey = `user:${id}`;
        const cached = await this.redis.get(cacheKey);
        if (cached) return JSON.parse(cached as string);

        const user = await this.prisma.user.findUnique({
            where: { id },
            select: USER_SELECT,
        });
        if (!user) throw new NotFoundException('User not found');

        await this.redis.set(cacheKey, JSON.stringify(user), 300);
        return user;
    }

    // ─── Get User Stats ──────────────────────────────────

    async getUserStats(userId: string): Promise<UserStatsDto> {
        const [properties, analyses, completedAnalyses, reports] = await Promise.all([
            this.prisma.property.count({ where: { ownerId: userId } }),
            this.prisma.analysis.count({
                where: { property: { ownerId: userId } },
            }),
            this.prisma.analysis.count({
                where: {
                    property: { ownerId: userId },
                    status: 'COMPLETED',
                },
            }),
            this.prisma.report.count({
                where: { analysis: { property: { ownerId: userId } } },
            }),
        ]);

        return {
            totalProperties: properties,
            totalAnalyses: analyses,
            completedAnalyses,
            totalReports: reports,
        };
    }

    // ─── Update Profile ──────────────────────────────────

    async updateProfile(userId: string, dto: UpdateUserProfileDto) {
        if (dto.email) {
            const exists = await this.prisma.user.findFirst({
                where: { email: dto.email, NOT: { id: userId } },
            });
            if (exists) throw new ConflictException('Email already in use');
        }

        const user = await this.prisma.user.update({
            where: { id: userId },
            data: dto,
            select: USER_SELECT,
        });

        await this.redis.del(`user:${userId}`);
        return user;
    }

    // ─── Admin: Update User ──────────────────────────────

    async adminUpdateUser(id: string, dto: AdminUpdateUserDto) {
        const user = await this.prisma.user.update({
            where: { id },
            data: dto,
            select: USER_SELECT,
        });

        await this.redis.del(`user:${id}`);
        return user;
    }

    // ─── Find All (Paginated) ────────────────────────────

    async findAll(query: SearchUserDto) {
        const { page = 1, limit = 10, sortBy = 'createdAt', sortDirection = 'desc', role, isActive, dateFilter } = query;
        const skip = (page - 1) * limit;

        const where: Prisma.UserWhereInput = {};
        if (role) where.role = role;
        if (isActive !== undefined) where.isActive = isActive;
        if (dateFilter) where.createdAt = { gte: this.getDateFilterStart(dateFilter) };

        const [users, total] = await Promise.all([
            this.prisma.user.findMany({
                where,
                select: USER_SELECT,
                skip,
                take: limit,
                orderBy: { [sortBy]: sortDirection },
            }),
            this.prisma.user.count({ where }),
        ]);

        return {
            data: users,
            meta: {
                total,
                page,
                limit,
                totalPages: Math.ceil(total / limit),
            },
        };
    }

    // ─── Search Users ────────────────────────────────────

    async searchUsers(query: SearchUserDto) {
        const { searchTerm, page = 1, limit = 10, sortBy = 'createdAt', sortDirection = 'desc', role, isActive } = query;

        const where: Prisma.UserWhereInput = {};

        if (searchTerm) {
            where.OR = [
                { email: { contains: searchTerm, mode: 'insensitive' } },
                { fullName: { contains: searchTerm, mode: 'insensitive' } },
            ];
        }
        if (role) where.role = role;
        if (isActive !== undefined) where.isActive = isActive;

        const skip = (page - 1) * limit;

        const [users, total] = await Promise.all([
            this.prisma.user.findMany({
                where,
                select: USER_SELECT,
                skip,
                take: limit,
                orderBy: { [sortBy]: sortDirection },
            }),
            this.prisma.user.count({ where }),
        ]);

        return {
            data: users,
            meta: {
                total,
                page,
                limit,
                totalPages: Math.ceil(total / limit),
            },
        };
    }

    // ─── Helpers ─────────────────────────────────────────

    private getDateFilterStart(filter: string): Date {
        const now = new Date();
        const map: Record<string, number> = {
            '24h': 1,
            '3d': 3,
            '7d': 7,
            '15d': 15,
            '30d': 30,
        };
        const days = map[filter] ?? 30;
        return new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
    }
}
