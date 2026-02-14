import { SetMetadata } from '@nestjs/common';
import { Permission, RoleType } from './permissions';

/**
 * Roles Decorator
 * 
 * Usage: @Roles(RoleType.ADMIN, RoleType.CONTRACTOR)
 */
export const ROLES_KEY = 'roles';
export const Roles = (...roles: RoleType[]) => SetMetadata(ROLES_KEY, roles);

/**
 * Permissions Decorator
 * 
 * Usage: @Permissions(Permission.TRADE_EXECUTE)
 */
export const PERMISSIONS_KEY = 'permissions';
export const Permissions = (...permissions: Permission[]) => SetMetadata(PERMISSIONS_KEY, permissions);

/**
 * Public Route Decorator
 * 
 * Skip authentication for public endpoints
 */
export const IS_PUBLIC_KEY = 'isPublic';
export const Public = () => SetMetadata(IS_PUBLIC_KEY, true);
