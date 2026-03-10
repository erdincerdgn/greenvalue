import { Module, OnModuleInit, Logger } from '@nestjs/common';
import { ReportController } from './report.controller';
import { ReportService } from './report.service';
import { AuthModule } from '../auth/auth.module';
import { AIProxyModule } from '../ai-proxy/ai-proxy.module';
import { QueueService } from '../core/bullmq/queue.service';

interface ReportJobData {
    analysisId: string;
    userId: string;
    format: string;
    locale: string;
}

@Module({
    imports: [AuthModule, AIProxyModule],
    controllers: [ReportController],
    providers: [ReportService],
    exports: [ReportService],
})
export class ReportModule implements OnModuleInit {
    private readonly logger = new Logger(ReportModule.name);

    constructor(
        private readonly reportService: ReportService,
        private readonly queueService: QueueService,
    ) {}

    async onModuleInit() {
        // Register BullMQ worker for the "reports" queue
        try {
            this.queueService.registerWorker(
                'reports',
                async (job: { id?: string; data: ReportJobData }) => {
                    this.logger.log(`Processing report job ${job.id ?? 'unknown'}: analysis=${job.data.analysisId}`);
                    await this.reportService.processReportJob(job.data);
                },
                2, // concurrency
            );
            this.logger.log('Report BullMQ worker registered on "reports" queue');
        } catch (error) {
            this.logger.warn(`Failed to register report worker: ${(error as Error).message}`);
        }
    }
}
