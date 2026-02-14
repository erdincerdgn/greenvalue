# ============================================================
# GreenValue AI Engine - Redis Queue Consumer
# BullMQ-compatible job consumer for image analysis pipeline
# ============================================================

import json
import asyncio
import logging
from typing import Optional, Callable, Awaitable

import redis.asyncio as aioredis

from config.settings import get_settings

logger = logging.getLogger(__name__)

# BullMQ queue/key naming convention
QUEUE_NAME = "analyze_image"
QUEUE_KEY = f"bull:{QUEUE_NAME}"


class QueueConsumer:
    """
    Redis-based queue consumer compatible with BullMQ (NestJS producer).

    BullMQ stores jobs in Redis using sorted sets and hashes:
    - bull:<queue>:wait     → List of waiting job IDs
    - bull:<queue>:<id>     → Hash with job data
    - bull:<queue>:active   → List of active job IDs
    - bull:<queue>:completed → Set of completed job IDs
    """

    def __init__(self):
        self.settings = get_settings()
        self.redis: Optional[aioredis.Redis] = None
        self._running = False
        self._handler: Optional[Callable] = None

    async def connect(self) -> None:
        """Connect to Redis."""
        self.redis = aioredis.from_url(
            self.settings.redis_url,
            decode_responses=True,
        )
        # Test connection
        await self.redis.ping()
        logger.info(f"Redis connected: {self.settings.redis_url}")

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("Redis disconnected")

    def register_handler(self, handler: Callable[..., Awaitable]) -> None:
        """Register a job processing handler function."""
        self._handler = handler
        logger.info(f"Handler registered for queue: {QUEUE_NAME}")

    async def start_consuming(self) -> None:
        """Start consuming jobs from the BullMQ queue."""
        if self._handler is None:
            raise RuntimeError("No handler registered. Call register_handler() first.")

        self._running = True
        logger.info(f"Queue consumer started: {QUEUE_NAME}")

        while self._running:
            try:
                # BRPOPLPUSH from wait list to active list (BullMQ pattern)
                job_id = await self.redis.brpoplpush(
                    f"{QUEUE_KEY}:wait",
                    f"{QUEUE_KEY}:active",
                    timeout=5,
                )

                if job_id is None:
                    continue  # Timeout, loop again

                # Fetch job data from hash
                job_data = await self.redis.hgetall(f"{QUEUE_KEY}:{job_id}")

                if not job_data:
                    logger.warning(f"Job {job_id} not found in Redis")
                    continue

                # Parse job payload
                try:
                    data = json.loads(job_data.get("data", "{}"))
                    logger.info(f"Processing job {job_id}: {data}")

                    # Execute handler
                    result = await self._handler(job_id, data)

                    # Mark as completed
                    await self._complete_job(job_id, result)

                except Exception as e:
                    logger.error(f"Job {job_id} failed: {e}", exc_info=True)
                    await self._fail_job(job_id, str(e))

            except asyncio.CancelledError:
                logger.info("Queue consumer cancelled")
                break
            except Exception as e:
                logger.error(f"Queue consumer error: {e}", exc_info=True)
                await asyncio.sleep(2)  # Backoff on error

    async def stop_consuming(self) -> None:
        """Stop the consumer loop."""
        self._running = False
        logger.info("Queue consumer stopping...")

    async def _complete_job(self, job_id: str, result: dict) -> None:
        """Mark a job as completed in BullMQ format."""
        try:
            # Move from active to completed
            await self.redis.lrem(f"{QUEUE_KEY}:active", 1, job_id)
            await self.redis.sadd(f"{QUEUE_KEY}:completed", job_id)

            # Store result
            await self.redis.hset(
                f"{QUEUE_KEY}:{job_id}",
                "returnvalue",
                json.dumps(result),
            )
            await self.redis.hset(
                f"{QUEUE_KEY}:{job_id}",
                "processedOn",
                str(int(asyncio.get_event_loop().time() * 1000)),
            )

            logger.info(f"Job {job_id} completed successfully")
        except Exception as e:
            logger.error(f"Failed to mark job {job_id} as completed: {e}")

    async def _fail_job(self, job_id: str, error: str) -> None:
        """Mark a job as failed in BullMQ format."""
        try:
            await self.redis.lrem(f"{QUEUE_KEY}:active", 1, job_id)
            await self.redis.sadd(f"{QUEUE_KEY}:failed", job_id)

            await self.redis.hset(
                f"{QUEUE_KEY}:{job_id}",
                "failedReason",
                error,
            )

            logger.warning(f"Job {job_id} marked as failed: {error}")
        except Exception as e:
            logger.error(f"Failed to mark job {job_id} as failed: {e}")

    async def publish_notification(self, channel: str, message: dict) -> None:
        """Publish a notification via Redis pub/sub."""
        if self.redis:
            await self.redis.publish(channel, json.dumps(message))
            logger.debug(f"Published to {channel}: {message}")


# Singleton
_consumer: Optional[QueueConsumer] = None


def get_queue_consumer() -> QueueConsumer:
    """Get or create singleton queue consumer."""
    global _consumer
    if _consumer is None:
        _consumer = QueueConsumer()
    return _consumer
