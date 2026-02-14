import { Injectable, CanActivate, ExecutionContext, ForbiddenException } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { ROLES_KEY, PERMISSIONS_KEY, IS_PUBLIC_KEY } from './decorators';
import { RoleType, Permission, hasPermission, hasAnyPermission } from './permissions';

@Injectable()
export class RolesGuard implements CanActivate {
    constructor(private reflector: Reflector) {}

    canActivate(context: ExecutionContext): boolean {
        const isPublic = this.reflector.getAllAndOverride<boolean>(IS_PUBLIC_KEY, [
            context.getHandler(),
            context.getClass(),
        ]);

        if (isPublic) return true;

        const requiredRoles = this.reflector.getAllAndOverride<RoleType[]>(ROLES_KEY, [
            context.getHandler(),
            context.getClass(),
        ]);

        const requiredPermissions = this.reflector.getAllAndOverride<Permission[]>(PERMISSIONS_KEY, [
            context.getHandler(),
            context.getClass(),
        ]);

        if (!requiredRoles?.length && !requiredPermissions?.length) return true;

        const request = context.switchToHttp().getRequest();
        const user = request.user;

        if (!user) {
            throw new ForbiddenException('User not authenticated');
        }

        if (requiredRoles?.length) {
            const userRole = user.role as RoleType;
            if (!requiredRoles.includes(userRole)) {
                throw new ForbiddenException(
                    `Role ${userRole} does not have access. Required: ${requiredRoles.join(', ')}`,
                );
            }
        }

        if (requiredPermissions?.length) {
            const userRole = user.role as RoleType;
            if (!hasAnyPermission(userRole, requiredPermissions)) {
                throw new ForbiddenException(
                    `Insufficient permissions. Required: ${requiredPermissions.join(', ')}`,
                );
            }
        }

        return true;
    }
}

@Injectable()
export class PermissionService {
    checkPermission(userRole: RoleType, permission: Permission): boolean {
        return hasPermission(userRole, permission);
    }

    checkPermissions(userRole: RoleType, permissions: Permission[]): boolean {
        return hasAnyPermission(userRole, permissions);
    }

    assertPermission(userRole: RoleType, permission: Permission): void {
        if (!this.checkPermission(userRole, permission)) {
            throw new ForbiddenException(`Permission denied: ${permission}`);
        }
    }
}
