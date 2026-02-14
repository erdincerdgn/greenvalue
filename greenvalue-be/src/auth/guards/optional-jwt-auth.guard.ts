import {
    Injectable,
    CanActivate,
    ExecutionContext,
    Logger,
} from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { PrismaService } from '../../core/prisma/prisma.service';

/**
 * Optional JWT Authentication Guard for GreenValue AI
 *
 * For endpoints that work with or without authentication.
 * If token is present and valid: attaches user to request.
 * If token is missing or invalid: request continues without user.
 */
@Injectable()
export class OptionalJwtAuthGuard implements CanActivate {
    private readonly logger = new Logger(OptionalJwtAuthGuard.name);

    constructor(
        private readonly jwtService: JwtService,
        private readonly prisma: PrismaService,
    ) {}

    async canActivate(context: ExecutionContext): Promise<boolean> {
        const request = context.switchToHttp().getRequest();
        const authHeader = request.headers.authorization;

        request.user = null;
        request.isAuthenticated = false;

        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return true;
        }

        const token = authHeader.split(' ')[1];
        if (!token || token.length < 10) {
            return true;
        }

        try {
            const payload = this.jwtService.verify(token, { ignoreExpiration: false });

            if (!payload.sub || !payload.email) {
                return true;
            }

            const user = await this.prisma.user.findUnique({
                where: { id: payload.sub },
            });

            if (!user) {
                return true;
            }

            if (user.isActive) {
                request.user = user;
                request.isAuthenticated = true;
                request.tokenPayload = payload;
            }

            return true;
        } catch (error) {
            this.logger.debug(`Optional auth - token validation failed: ${error.message}`);
            return true;
        }
    }
}
