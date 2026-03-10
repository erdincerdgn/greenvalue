import {
    Injectable,
    Logger,
    OnModuleInit,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as Minio from 'minio';

export interface UploadResult {
    bucket: string;
    key: string;
    etag: string;
    size?: number;
}

/**
 * S3-Compatible Object Storage Service for GreenValue AI Platform
 * Backend: RustFS (Apache 2.0, Rust-based, 2.3x faster than MinIO)
 * Client:  minio-js (standard S3 client — works with any S3-compatible storage)
 *
 * Buckets:
 * - raw-uploads:  User-uploaded building images
 * - ai-heatmaps:  AI-generated thermal heatmap overlays
 * - pdf-reports:  Generated PDF / DOCX reports
 */
@Injectable()
export class StorageService implements OnModuleInit {
    private readonly logger = new Logger(StorageService.name);
    /** Internal client — used for server-side uploads, downloads, bucket ops */
    private client: Minio.Client;
    /** Public client — used ONLY for presigned URL generation with external hostname */
    private publicClient: Minio.Client;

    public static readonly BUCKETS = {
        RAW_UPLOADS: 'raw-uploads',
        AI_HEATMAPS: 'ai-heatmaps',
        PDF_REPORTS: 'pdf-reports',
    };

    constructor(private readonly config: ConfigService) {}

    async onModuleInit() {
        const endPoint = this.config.get('MINIO_ENDPOINT', 'localhost');
        const port = parseInt(this.config.get('MINIO_PORT', '9000'), 10);
        const useSSL = this.config.get('MINIO_USE_SSL', 'false') === 'true';
        const accessKey = this.config.get('MINIO_ACCESS_KEY', 'greenvalue');
        const secretKey = this.config.get('MINIO_SECRET_KEY', 'greenvalue_secret');

        // Internal client talks to RustFS inside Docker network
        this.client = new Minio.Client({
            endPoint,
            port,
            useSSL,
            accessKey,
            secretKey,
        });

        // Public client generates presigned URLs with the external hostname/port
        // so mobile/browser can PUT/GET directly. Signature is bound to Host header,
        // so we need a separate client with the public endpoint.
        const publicUrl = this.config.get('MINIO_PUBLIC_URL', '');
        if (publicUrl) {
            const parsed = new URL(publicUrl);
            this.publicClient = new Minio.Client({
                endPoint: parsed.hostname,
                port: parseInt(parsed.port || (parsed.protocol === 'https:' ? '443' : '80'), 10),
                useSSL: parsed.protocol === 'https:',
                accessKey,
                secretKey,
                region: 'us-east-1', // Explicit region prevents network call for GetBucketLocation
            });
            this.logger.log(`Presigned URLs will use public endpoint: ${publicUrl}`);
        } else {
            this.publicClient = this.client;
            this.logger.log('Presigned URLs use internal endpoint (no MINIO_PUBLIC_URL set)');
        }

        await this.ensureBuckets();
        this.logger.log('✅ RustFS (S3) connected and buckets verified');
    }

    // ─── Bucket Management ───────────────────────────────

    private async ensureBuckets(): Promise<void> {
        for (const bucket of Object.values(StorageService.BUCKETS)) {
            const exists = await this.client.bucketExists(bucket);
            if (!exists) {
                await this.client.makeBucket(bucket, 'us-east-1');
                this.logger.log(`Created bucket: ${bucket}`);
            }
        }
    }

    // ─── Upload ──────────────────────────────────────────

    async upload(
        bucket: string,
        key: string,
        data: Buffer | NodeJS.ReadableStream,
        metadata?: Record<string, string>,
    ): Promise<UploadResult> {
        const metaData = metadata ?? {};
        const result = await this.client.putObject(bucket, key, data, undefined, metaData);

        this.logger.debug(`Uploaded ${key} to ${bucket}`);
        return {
            bucket,
            key,
            etag: result.etag,
        };
    }

    // ─── Download ────────────────────────────────────────

    async download(bucket: string, key: string): Promise<NodeJS.ReadableStream> {
        return this.client.getObject(bucket, key);
    }

    async downloadAsBuffer(bucket: string, key: string): Promise<Buffer> {
        const stream = await this.client.getObject(bucket, key);
        const chunks: Buffer[] = [];
        return new Promise((resolve, reject) => {
            stream.on('data', (chunk) => chunks.push(chunk));
            stream.on('end', () => resolve(Buffer.concat(chunks)));
            stream.on('error', reject);
        });
    }

    // ─── Presigned URLs ──────────────────────────────────

    async getPresignedUploadUrl(
        bucket: string,
        key: string,
        expirySeconds = 3600,
    ): Promise<string> {
        // Use publicClient so the signature matches the Host the mobile/browser will actually send
        return this.publicClient.presignedPutObject(bucket, key, expirySeconds);
    }

    async getPresignedDownloadUrl(
        bucket: string,
        key: string,
        expirySeconds = 3600,
    ): Promise<string> {
        return this.publicClient.presignedGetObject(bucket, key, expirySeconds);
    }

    // ─── Object Info & Delete ────────────────────────────

    async stat(bucket: string, key: string): Promise<Minio.BucketItemStat> {
        return this.client.statObject(bucket, key);
    }

    async delete(bucket: string, key: string): Promise<void> {
        await this.client.removeObject(bucket, key);
        this.logger.debug(`Deleted ${key} from ${bucket}`);
    }

    async exists(bucket: string, key: string): Promise<boolean> {
        try {
            await this.client.statObject(bucket, key);
            return true;
        } catch {
            return false;
        }
    }

    // ─── List Objects ────────────────────────────────────

    async listObjects(bucket: string, prefix?: string): Promise<Minio.BucketItem[]> {
        return new Promise((resolve, reject) => {
            const items: Minio.BucketItem[] = [];
            const stream = this.client.listObjects(bucket, prefix, true);
            stream.on('data', (item) => items.push(item));
            stream.on('end', () => resolve(items));
            stream.on('error', reject);
        });
    }

    // ─── Health Check ────────────────────────────────────

    async healthCheck(): Promise<{ status: string }> {
        try {
            await this.client.listBuckets();
            return { status: 'healthy' };
        } catch {
            return { status: 'unhealthy' };
        }
    }
}
