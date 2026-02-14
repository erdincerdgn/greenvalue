import {
    WebSocketGateway,
    WebSocketServer,
    SubscribeMessage,
    OnGatewayInit,
    OnGatewayConnection,
    OnGatewayDisconnect,
    MessageBody,
    ConnectedSocket,
} from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';
import { Logger } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';

@WebSocketGateway({
    cors: {
        origin: '*',
    },
    namespace: '/analysis',
    pingInterval: 10000,
    pingTimeout: 5000,
})
export class EventsGateway implements OnGatewayInit, OnGatewayConnection, OnGatewayDisconnect {
    @WebSocketServer()
    server: Server;

    private readonly logger = new Logger(EventsGateway.name);
    private connectedClients: Map<string, ClientInfo> = new Map();

    constructor(private readonly jwtService: JwtService) {}

    async afterInit(_server: Server) {
        this.logger.log('🔌 WebSocket Gateway initializing...');
        this.logger.log('✅ WebSocket Gateway initialized');
    }

    async handleConnection(client: Socket) {
        try {
            const token = client.handshake.auth?.token ||
                client.handshake.headers?.authorization?.split(' ')[1];

            if (!token) {
                this.logger.warn(`Client ${client.id} rejected: No token`);
                client.emit('error', { code: 'AUTH_REQUIRED', message: 'Authentication required' });
                client.disconnect();
                return;
            }

            const payload = this.jwtService.verify(token);
            const userId: string = payload.sub;

            this.connectedClients.set(client.id, {
                userId,
                socket: client,
                connectedAt: new Date(),
                subscriptions: [],
            });

            client.join(`user:${userId}`);

            this.logger.log(`✅ Connected: ${client.id} (User: ${userId}) | Total: ${this.connectedClients.size}`);

            client.emit('connected', {
                message: 'Connected to GreenValue AI',
                userId,
                timestamp: new Date().toISOString(),
            });

            this.setupHeartbeat(client);
        } catch (error) {
            this.logger.error(`Connection error ${client.id}: ${error.message}`);
            client.emit('error', { code: 'AUTH_FAILED', message: 'Invalid token' });
            client.disconnect();
        }
    }

    handleDisconnect(client: Socket) {
        const clientInfo = this.connectedClients.get(client.id);
        if (clientInfo) {
            this.logger.log(`👋 Disconnected: ${client.id} (User: ${clientInfo.userId}) | Total: ${this.connectedClients.size - 1}`);
            this.connectedClients.delete(client.id);
        }
    }

    private setupHeartbeat(client: Socket): void {
        const interval = setInterval(() => {
            if (!this.connectedClients.has(client.id)) {
                clearInterval(interval);
                return;
            }
            client.emit('heartbeat', { timestamp: Date.now() });
        }, 30000);

        client.on('disconnect', () => clearInterval(interval));
    }

    // ==========================================
    // SUBSCRIPTION HANDLERS
    // ==========================================

    @SubscribeMessage('subscribe:analysis')
    handleSubscribeAnalysis(
        @ConnectedSocket() client: Socket,
        @MessageBody() data: { jobId: string },
    ) {
        if (data.jobId) {
            client.join(`analysis:${data.jobId}`);
            this.logger.debug(`${client.id} subscribed to analysis: ${data.jobId}`);
            return { event: 'subscribed', data: { channel: 'analysis', jobId: data.jobId } };
        }
        return { event: 'error', data: { message: 'jobId is required' } };
    }

    @SubscribeMessage('unsubscribe:analysis')
    handleUnsubscribeAnalysis(
        @ConnectedSocket() client: Socket,
        @MessageBody() data: { jobId: string },
    ) {
        if (data.jobId) {
            client.leave(`analysis:${data.jobId}`);
        }
        return { event: 'unsubscribed', data: { channel: 'analysis', jobId: data.jobId } };
    }

    @SubscribeMessage('subscribe:property')
    handleSubscribeProperty(
        @ConnectedSocket() client: Socket,
        @MessageBody() data: { propertyId: string },
    ) {
        if (data.propertyId) {
            client.join(`property:${data.propertyId}`);
            return { event: 'subscribed', data: { channel: 'property', propertyId: data.propertyId } };
        }
        return { event: 'error', data: { message: 'propertyId is required' } };
    }

    @SubscribeMessage('subscribe:notifications')
    handleSubscribeNotifications(@ConnectedSocket() client: Socket) {
        const clientInfo = this.connectedClients.get(client.id);
        if (clientInfo) {
            client.join(`notifications:${clientInfo.userId}`);
            return { event: 'subscribed', data: { channel: 'notifications' } };
        }
        return { event: 'error', data: { message: 'Not authenticated' } };
    }

    // ==========================================
    // BROADCAST METHODS (called from services)
    // ==========================================

    /**
     * Send analysis progress update to subscribers
     */
    sendAnalysisProgress(jobId: string, progress: AnalysisProgress): void {
        this.server.to(`analysis:${jobId}`).emit('analysis:progress', {
            jobId,
            ...progress,
            timestamp: new Date().toISOString(),
        });
    }

    /**
     * Send analysis completion to subscribers and the user
     */
    sendAnalysisCompleted(userId: string, jobId: string, result: AnalysisResult): void {
        this.server.to(`analysis:${jobId}`).emit('analysis:completed', {
            jobId,
            ...result,
            timestamp: new Date().toISOString(),
        });

        this.server.to(`user:${userId}`).emit('analysis:completed', {
            jobId,
            ...result,
            timestamp: new Date().toISOString(),
        });
    }

    /**
     * Send analysis failure notification
     */
    sendAnalysisFailed(userId: string, jobId: string, error: string): void {
        const payload = {
            jobId,
            status: 'FAILED',
            error,
            timestamp: new Date().toISOString(),
        };
        this.server.to(`analysis:${jobId}`).emit('analysis:failed', payload);
        this.server.to(`user:${userId}`).emit('analysis:failed', payload);
    }

    /**
     * Send report generation completion
     */
    sendReportReady(userId: string, data: { analysisId: string; reportId: string; format: string }): void {
        this.server.to(`user:${userId}`).emit('report:ready', {
            ...data,
            timestamp: new Date().toISOString(),
        });
    }

    /**
     * Send notification to specific user
     */
    sendNotification(userId: string, notification: UserNotification): void {
        this.server.to(`user:${userId}`).emit('notification', {
            ...notification,
            timestamp: new Date().toISOString(),
        });
    }

    /**
     * Broadcast to a specific room
     */
    broadcastToRoom(room: string, event: string, payload: any): void {
        this.server.to(room).emit(event, {
            ...payload,
            timestamp: new Date().toISOString(),
        });
    }

    /**
     * Broadcast system-wide message
     */
    broadcastSystemMessage(message: string, type: 'info' | 'warning' | 'error' = 'info'): void {
        this.server.emit('system', {
            message,
            type,
            timestamp: new Date().toISOString(),
        });
    }

    /**
     * Broadcast to all connected clients
     */
    broadcast(event: string, payload: any): void {
        this.server.emit(event, {
            ...payload,
            timestamp: new Date().toISOString(),
        });
    }

    // ==========================================
    // UTILITY METHODS
    // ==========================================

    getConnectedClientsCount(): number {
        return this.connectedClients.size;
    }

    isUserConnected(userId: string): boolean {
        for (const [, info] of this.connectedClients) {
            if (info.userId === userId) return true;
        }
        return false;
    }

    getClientsByUserId(userId: string): ClientInfo[] {
        const clients: ClientInfo[] = [];
        for (const [, info] of this.connectedClients) {
            if (info.userId === userId) clients.push(info);
        }
        return clients;
    }

    getServer(): Server {
        return this.server;
    }
}

// ==========================================
// TYPES
// ==========================================

interface ClientInfo {
    userId: string;
    socket: Socket;
    connectedAt: Date;
    subscriptions: string[];
}

interface AnalysisProgress {
    status: string;
    step?: string;
    percent?: number;
    message?: string;
}

interface AnalysisResult {
    status: 'COMPLETED';
    detections?: number;
    energyLabel?: string;
    overallUValue?: number;
}

interface UserNotification {
    title: string;
    message: string;
    type: 'info' | 'success' | 'warning' | 'error';
    action?: string;
}

export { ClientInfo, AnalysisProgress, AnalysisResult, UserNotification };
