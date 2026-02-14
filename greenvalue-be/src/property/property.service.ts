import { Injectable, NotFoundException, ForbiddenException } from '@nestjs/common';
import { PrismaService } from '../core/prisma/prisma.service';
import { EventEmitter2 } from '@nestjs/event-emitter';
import { CreatePropertyDto, UpdatePropertyDto, PropertyListQueryDto } from './dto';
import { Prisma, Role } from '@prisma/client';

@Injectable()
export class PropertyService {
    constructor(
        private readonly prisma: PrismaService,
        private readonly eventEmitter: EventEmitter2,
    ) {}

    // ─── Create ──────────────────────────────────────────

    async create(userId: string, dto: CreatePropertyDto) {
        const property = await this.prisma.property.create({
            data: {
                ...dto,
                ownerId: userId,
            },
            include: {
                _count: { select: { analyses: true } },
            },
        });

        this.eventEmitter.emit('property.created', {
            userId,
            propertyId: property.id,
            title: property.title,
            address: property.address,
        });

        return this.formatResponse(property);
    }

    // ─── Find All (User's Properties) ────────────────────

    async findAllByUser(userId: string, query: PropertyListQueryDto) {
        const { page = 1, limit = 10, search, city, buildingType, sortBy = 'createdAt', sortDirection = 'desc' } = query;
        const skip = (page - 1) * limit;

        const where: Prisma.PropertyWhereInput = { ownerId: userId };
        if (search) {
            where.OR = [
                { title: { contains: search, mode: 'insensitive' } },
                { address: { contains: search, mode: 'insensitive' } },
            ];
        }
        if (city) where.city = { contains: city, mode: 'insensitive' };
        if (buildingType) where.buildingType = buildingType;

        const [properties, total] = await Promise.all([
            this.prisma.property.findMany({
                where,
                include: { _count: { select: { analyses: true } } },
                skip,
                take: limit,
                orderBy: { [sortBy]: sortDirection },
            }),
            this.prisma.property.count({ where }),
        ]);

        return {
            data: properties.map(this.formatResponse),
            meta: { total, page, limit, totalPages: Math.ceil(total / limit) },
        };
    }

    // ─── Find All (Admin) ────────────────────────────────

    async findAll(query: PropertyListQueryDto) {
        const { page = 1, limit = 10, search, city, buildingType, sortBy = 'createdAt', sortDirection = 'desc' } = query;
        const skip = (page - 1) * limit;

        const where: Prisma.PropertyWhereInput = {};
        if (search) {
            where.OR = [
                { title: { contains: search, mode: 'insensitive' } },
                { address: { contains: search, mode: 'insensitive' } },
            ];
        }
        if (city) where.city = { contains: city, mode: 'insensitive' };
        if (buildingType) where.buildingType = buildingType;

        const [properties, total] = await Promise.all([
            this.prisma.property.findMany({
                where,
                include: {
                    owner: { select: { id: true, fullName: true, email: true } },
                    _count: { select: { analyses: true } },
                },
                skip,
                take: limit,
                orderBy: { [sortBy]: sortDirection },
            }),
            this.prisma.property.count({ where }),
        ]);

        return {
            data: properties.map(this.formatResponse),
            meta: { total, page, limit, totalPages: Math.ceil(total / limit) },
        };
    }

    // ─── Find One ────────────────────────────────────────

    async findOne(id: string, userId: string, userRole: Role) {
        const property = await this.prisma.property.findUnique({
            where: { id },
            include: {
                owner: { select: { id: true, fullName: true, email: true } },
                analyses: {
                    orderBy: { createdAt: 'desc' },
                    take: 10,
                    select: {
                        id: true,
                        jobId: true,
                        status: true,
                        energyLabel: true,
                        overallUValue: true,
                        createdAt: true,
                    },
                },
                _count: { select: { analyses: true } },
            },
        });

        if (!property) throw new NotFoundException('Property not found');
        if (property.ownerId !== userId && userRole !== Role.ADMIN) {
            throw new ForbiddenException('Access denied');
        }

        return property;
    }

    // ─── Update ──────────────────────────────────────────

    async update(id: string, userId: string, userRole: Role, dto: UpdatePropertyDto) {
        const existing = await this.prisma.property.findUnique({ where: { id } });
        if (!existing) throw new NotFoundException('Property not found');
        if (existing.ownerId !== userId && userRole !== Role.ADMIN) {
            throw new ForbiddenException('Access denied');
        }

        const updated = await this.prisma.property.update({
            where: { id },
            data: dto,
            include: { _count: { select: { analyses: true } } },
        });

        return this.formatResponse(updated);
    }

    // ─── Delete ──────────────────────────────────────────

    async remove(id: string, userId: string, userRole: Role) {
        const existing = await this.prisma.property.findUnique({ where: { id } });
        if (!existing) throw new NotFoundException('Property not found');
        if (existing.ownerId !== userId && userRole !== Role.ADMIN) {
            throw new ForbiddenException('Access denied');
        }

        await this.prisma.property.delete({ where: { id } });
        return { deleted: true, id };
    }

    // ─── Helpers ─────────────────────────────────────────

    private formatResponse(property: any) {
        return {
            id: property.id,
            title: property.title,
            address: property.address,
            city: property.city,
            district: property.district,
            buildingYear: property.buildingYear,
            buildingType: property.buildingType,
            floorArea: property.floorArea ? Number(property.floorArea) : null,
            thumbnailKey: property.thumbnailKey,
            ownerId: property.ownerId,
            owner: property.owner,
            createdAt: property.createdAt,
            updatedAt: property.updatedAt,
            analysisCount: property._count?.analyses ?? 0,
            analyses: property.analyses,
        };
    }
}
