import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { EventEmitterModule } from '@nestjs/event-emitter';
import { ScheduleModule } from '@nestjs/schedule';
import { ThrottlerModule, ThrottlerGuard } from '@nestjs/throttler';
import { APP_GUARD } from '@nestjs/core';
import { AppController } from './app.controller';
import { AppService } from './app.service';

// Core modules
import { PrismaModule } from './core/prisma/prisma.module';
import { RedisModule } from './core/redis/redis.module';
import { BullMQModule } from './core/bullmq/bullmq.module';
import { StorageModule } from './core/storage/storage.module';

// Feature modules
import { AuthModule } from './auth/auth.module';
import { UserModule } from './user/user.module';
import { PropertyModule } from './property/property.module';
import { AIProxyModule } from './ai-proxy/ai-proxy.module';
import { AuditModule } from './audit/audit.module';
import { HealthModule } from './health/health.module';
import { MetricsModule } from './metrics/metrics.module';
import { WebSocketModule } from './websocket/websocket.module';

@Module({
    imports: [
        // Configuration
        ConfigModule.forRoot({
            isGlobal: true,
            envFilePath: ['.env.local', '.env'],
        }),

        // Event Emitter (for analysis events, notifications)
        EventEmitterModule.forRoot(),

        // Schedule Module (cron jobs)
        ScheduleModule.forRoot(),

        // Rate Limiting
        ThrottlerModule.forRoot([{
            ttl: 60000,
            limit: 100,
        }]),

        // Core infrastructure
        PrismaModule,
        RedisModule,
        BullMQModule,
        StorageModule,

        // Feature modules
        AuthModule,
        UserModule,
        PropertyModule,
        AIProxyModule,
        AuditModule,
        HealthModule,
        MetricsModule,
        WebSocketModule,
    ],
    controllers: [AppController],
    providers: [
        AppService,
        {
            provide: APP_GUARD,
            useClass: ThrottlerGuard,
        },
    ],
})
export class AppModule {}

