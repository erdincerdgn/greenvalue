import {
    Injectable,
    CanActivate,
    ExecutionContext,
    UnauthorizedException,
    ForbiddenException,
    Logger,
} from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { PrismaService } from '../../core/prisma/prisma.service';

/**
 * JWT Authentication Guard for GreenValue AI
 *
 * Security checks:
 * 1. Valid JWT token
 * 2. User exists in database
 * 3. User isActive
 */
@Injectable()
export class JwtAuthGuard implements CanActivate {
    private readonly logger = new Logger(JwtAuthGuard.name);

    constructor(
        private readonly jwtService: JwtService,
        private readonly prisma: PrismaService,
    ) {}

    async canActivate(context: ExecutionContext): Promise<boolean> {
        const request = context.switchToHttp().getRequest();
        const authHeader = request.headers.authorization;

        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            throw new UnauthorizedException('Missing or invalid authorization token');
        }

        const token = authHeader.split(' ')[1];
        if (!token || token.length < 10) {
            throw new UnauthorizedException('Invalid token format');
        }

        try {
            const payload = this.jwtService.verify(token, { ignoreExpiration: false });

            if (!payload.sub || !payload.email) {
                throw new UnauthorizedException('Invalid token payload');
            }

            const user = await this.prisma.user.findUnique({
                where: { id: payload.sub },
            });

            if (!user) {
                throw new UnauthorizedException('User not found');
            }

            if (!user.isActive) {
                this.logger.warn(`Access denied for deactivated user ${user.id}`);
                throw new ForbiddenException('Your account has been deactivated. Please contact support.');
            }

            // Attach user to request
            request.user = user;
            request.tokenPayload = payload;

            return true;
        } catch (error) {
            if (error.name === 'TokenExpiredError') {
                throw new UnauthorizedException('Token has expired');
            }
            if (error.name === 'JsonWebTokenError') {
                throw new UnauthorizedException('Invalid token');
            }
            if (error instanceof UnauthorizedException || error instanceof ForbiddenException) {
                throw error;
            }

            this.logger.error(`Unexpected auth error: ${error.message}`, error.stack);
            throw new UnauthorizedException('Authentication failed');
        }
    }
}
