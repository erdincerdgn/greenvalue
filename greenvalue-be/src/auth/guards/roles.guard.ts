import {
    Injectable,
    CanActivate,
    ExecutionContext,
    ForbiddenException,
    Logger,
    SetMetadata,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Role } from '@prisma/client';

export const ROLES_KEY = 'roles';
export const FEATURES_KEY = 'features';

@Injectable()
export class RolesGuard implements CanActivate {
    private readonly logger = new Logger(RolesGuard.name);

    constructor(private reflector: Reflector) {}

    canActivate(context: ExecutionContext): boolean {
        const requiredRoles = this.reflector.getAllAndOverride<Role[]>(ROLES_KEY, [
            context.getHandler(),
            context.getClass(),
        ]);

        if (!requiredRoles) return true;

        const { user } = context.switchToHttp().getRequest();
        if (!user) {
            throw new ForbiddenException('Authentication required');
        }

        const hasRole = requiredRoles.includes(user.role);
        if (!hasRole) {
            this.logger.warn(`User ${user.id} with role ${user.role} denied access`);
            throw new ForbiddenException('Insufficient role permissions');
        }

        return true;
    }
}

/** Decorator – restrict endpoint to specific roles */
export const Roles = (...roles: Role[]) => SetMetadata(ROLES_KEY, roles);

/** Decorator – require specific feature flags (reserved for future use) */
export const RequiresFeature = (...features: string[]) => SetMetadata(FEATURES_KEY, features);

@Injectable()
export class SubscriptionGuard implements CanActivate {
    canActivate(context: ExecutionContext): boolean {
        const { user } = context.switchToHttp().getRequest();
        if (!user) {
            throw new ForbiddenException('Authentication required');
        }
        // For GreenValue, all active users have access
        if (!user.isActive) {
            throw new ForbiddenException('Account is not active');
        }
        return true;
    }
}
