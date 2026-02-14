import {
    Injectable,
    CanActivate,
    ExecutionContext,
    UnauthorizedException,
    ForbiddenException,
    Logger,
} from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { Role } from '@prisma/client';
import { PrismaService } from '../../core/prisma/prisma.service';

/**
 * Admin Panel Authentication Guard for GreenValue AI
 *
 * Security checks:
 * 1. Valid JWT token with 'admin' tokenType
 * 2. User exists and is active
 * 3. User has ADMIN role
 * 4. IP whitelist (optional)
 */
@Injectable()
export class AdminAuthGuard implements CanActivate {
    private readonly logger = new Logger(AdminAuthGuard.name);

    private readonly ADMIN_IP_WHITELIST: string[] = [];
    private readonly ENABLE_IP_WHITELIST = false;

    constructor(
        private readonly jwtService: JwtService,
        private readonly prisma: PrismaService,
    ) {}

    async canActivate(context: ExecutionContext): Promise<boolean> {
        const request = context.switchToHttp().getRequest();
        const authHeader = request.headers.authorization;
        const clientIp = request.ip || request.connection?.remoteAddress;

        // 1. IP Whitelist check (if enabled)
        if (this.ENABLE_IP_WHITELIST && this.ADMIN_IP_WHITELIST.length > 0) {
            if (!this.ADMIN_IP_WHITELIST.includes(clientIp)) {
                this.logger.warn(`Admin access attempt from non-whitelisted IP: ${clientIp}`);
                throw new ForbiddenException('Admin access not allowed from this location');
            }
        }

        // 2. Check authorization header
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            throw new UnauthorizedException('Missing or invalid authorization token');
        }

        const token = authHeader.split(' ')[1];
        if (!token || token.length < 10) {
            throw new UnauthorizedException('Invalid token format');
        }

        try {
            // 3. Verify JWT token
            const payload = this.jwtService.verify(token, { ignoreExpiration: false });

            // 4. Check admin token type
            if (payload.tokenType !== 'admin') {
                this.logger.warn(`Non-admin token used for admin panel. User: ${payload.sub}`);
                throw new UnauthorizedException('Admin panel access requires admin authentication');
            }

            if (!payload.sub || !payload.email) {
                throw new UnauthorizedException('Invalid token payload');
            }

            // 5. Get user from database
            const user = await this.prisma.user.findUnique({
                where: { id: payload.sub },
            });

            if (!user) {
                throw new UnauthorizedException('User not found');
            }

            // 6. Check user is active
            if (!user.isActive) {
                this.logger.warn(`Admin access denied - User ${user.id} is deactivated`);
                throw new ForbiddenException('Account is deactivated. Admin access denied.');
            }

            // 7. Check admin role
            if (user.role !== Role.ADMIN) {
                this.logger.warn(`Admin access denied - User ${user.id} role: ${user.role} from IP: ${clientIp}`);
                throw new ForbiddenException('You do not have permission to access the admin panel');
            }

            // 8. Log successful access
            this.logger.log(`Admin access granted - User: ${user.email}, IP: ${clientIp}`);

            // 9. Attach user to request
            request.user = user;
            request.tokenPayload = payload;
            request.isAdmin = true;

            return true;
        } catch (error) {
            if (error.name === 'TokenExpiredError') {
                throw new UnauthorizedException('Admin token has expired');
            }
            if (error.name === 'JsonWebTokenError') {
                throw new UnauthorizedException('Invalid admin token');
            }
            if (error instanceof UnauthorizedException || error instanceof ForbiddenException) {
                throw error;
            }

            this.logger.error(`Admin auth error: ${error.message}`, error.stack);
            throw new UnauthorizedException('Admin authentication failed');
        }
    }
}
