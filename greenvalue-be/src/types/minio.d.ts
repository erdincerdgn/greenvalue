/* eslint-disable @typescript-eslint/no-explicit-any */
declare module 'minio' {
    export interface ClientOptions {
        endPoint: string;
        port?: number;
        useSSL?: boolean;
        accessKey: string;
        secretKey: string;
        region?: string;
        transport?: any;
        sessionToken?: string;
        partSize?: number;
        pathStyle?: boolean;
    }

    export interface BucketItem {
        name: string;
        prefix: string;
        size: number;
        etag: string;
        lastModified: Date;
    }

    export interface BucketItemStat {
        size: number;
        etag: string;
        lastModified: Date;
        metaData: Record<string, string>;
    }

    export interface UploadedObjectInfo {
        etag: string;
        versionId: string | null;
    }

    export class Client {
        constructor(options: ClientOptions);
        bucketExists(bucket: string): Promise<boolean>;
        makeBucket(bucket: string, region?: string): Promise<void>;
        putObject(bucket: string, name: string, stream: any, size?: number, metaData?: Record<string, string>): Promise<UploadedObjectInfo>;
        getObject(bucket: string, name: string): Promise<NodeJS.ReadableStream>;
        statObject(bucket: string, name: string): Promise<BucketItemStat>;
        removeObject(bucket: string, name: string): Promise<void>;
        presignedPutObject(bucket: string, name: string, expiry?: number): Promise<string>;
        presignedGetObject(bucket: string, name: string, expiry?: number): Promise<string>;
        listBuckets(): Promise<Array<{ name: string; creationDate: Date }>>;
        listObjects(bucket: string, prefix?: string, recursive?: boolean): any;
    }
}
