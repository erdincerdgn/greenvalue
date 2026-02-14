import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { ConfigModule } from '@nestjs/config';

import { AIProxyController } from './ai-proxy.controller';
import { AIProxyService } from './ai-proxy.service';
import { GrpcClientService } from './grpc-client.service';
import { AuthModule } from '../auth/auth.module';

@Module({
    imports: [
        HttpModule.register({
            timeout: 120000, // 2 minute timeout for AI Engine calls
            maxRedirects: 3,
            headers: { 'Content-Type': 'application/json' },
        }),
        ConfigModule,
        AuthModule,
    ],
    controllers: [AIProxyController],
    providers: [AIProxyService, GrpcClientService],
    exports: [AIProxyService, GrpcClientService],
})
export class AIProxyModule {}
