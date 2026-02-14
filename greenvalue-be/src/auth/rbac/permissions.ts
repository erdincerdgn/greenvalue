export enum Permission {
    // User management
    USER_READ = 'user:read',
    USER_WRITE = 'user:write',
    USER_DELETE = 'user:delete',
    USER_MANAGE = 'user:manage',

    // Property management
    PROPERTY_READ = 'property:read',
    PROPERTY_WRITE = 'property:write',
    PROPERTY_DELETE = 'property:delete',
    PROPERTY_MANAGE = 'property:manage',

    // Analysis
    ANALYSIS_READ = 'analysis:read',
    ANALYSIS_CREATE = 'analysis:create',
    ANALYSIS_MANAGE = 'analysis:manage',

    // Reports
    REPORT_READ = 'report:read',
    REPORT_CREATE = 'report:create',
    REPORT_MANAGE = 'report:manage',

    // Admin
    ADMIN_READ = 'admin:read',
    ADMIN_WRITE = 'admin:write',
    ADMIN_FULL = 'admin:full',

    // Audit
    AUDIT_READ = 'audit:read',
    AUDIT_EXPORT = 'audit:export',

    // System
    SYSTEM_CONFIG = 'system:config',
    SYSTEM_MONITOR = 'system:monitor',
}

export enum RoleType {
    OWNER = 'OWNER',
    CONTRACTOR = 'CONTRACTOR',
    ADMIN = 'ADMIN',
}

export const RolePermissions: Record<RoleType, Permission[]> = {
    [RoleType.OWNER]: [
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.PROPERTY_READ,
        Permission.PROPERTY_WRITE,
        Permission.PROPERTY_DELETE,
        Permission.ANALYSIS_READ,
        Permission.ANALYSIS_CREATE,
        Permission.REPORT_READ,
        Permission.REPORT_CREATE,
    ],

    [RoleType.CONTRACTOR]: [
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.PROPERTY_READ,
        Permission.ANALYSIS_READ,
        Permission.ANALYSIS_CREATE,
        Permission.REPORT_READ,
        Permission.REPORT_CREATE,
    ],

    [RoleType.ADMIN]: Object.values(Permission),
};

export function hasPermission(role: RoleType, permission: Permission): boolean {
    return RolePermissions[role]?.includes(permission) ?? false;
}

export function hasAnyPermission(role: RoleType, permissions: Permission[]): boolean {
    return permissions.some((p) => hasPermission(role, p));
}

export function hasAllPermissions(role: RoleType, permissions: Permission[]): boolean {
    return permissions.every((p) => hasPermission(role, p));
}
