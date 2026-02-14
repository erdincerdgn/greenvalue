import { Module } from '@nestjs/common';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';
import { AuthService } from './auth.service';
import { AuthController } from './auth.controller';
import { PrismaModule } from '../core/prisma/prisma.module';

import { JwtAuthGuard } from './guards/jwt-auth.guard';
import { AdminAuthGuard } from './guards/admin-auth.guard';
import { OptionalJwtAuthGuard } from './guards/optional-jwt-auth.guard';
import { RolesGuard, SubscriptionGuard } from './guards/roles.guard';

import { RolesGuard as RbacRolesGuard, PermissionService } from './rbac/roles.guard';

import { GoogleStrategy } from './strategies/google.strategy';
import { GithubStrategy } from './strategies/github.strategy';

import { OAuthController } from './oauth/oauth.controller';

const jwtSecret = process.env.JWT_SECRET || 'greenvalue-super-secret-key';

@Module({
    imports: [
        PrismaModule,
        PassportModule.register({ defaultStrategy: 'jwt' }),
        JwtModule.register({
            secret: jwtSecret,
            signOptions: {
                expiresIn: '30d',
                issuer: 'greenvalue',
                audience: 'greenvalue-api',
            },
        }),
    ],
    controllers: [AuthController, OAuthController],
    providers: [
        AuthService,
        JwtAuthGuard,
        AdminAuthGuard,
        OptionalJwtAuthGuard,
        RolesGuard,
        SubscriptionGuard,
        RbacRolesGuard,
        PermissionService,
        GoogleStrategy,
        GithubStrategy,
    ],
    exports: [
        AuthService,
        JwtModule,
        PassportModule,
        JwtAuthGuard,
        AdminAuthGuard,
        OptionalJwtAuthGuard,
        RolesGuard,
        SubscriptionGuard,
        RbacRolesGuard,
        PermissionService,
    ],
})
export class AuthModule {}

