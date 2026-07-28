"""
Enterprise Knowledge Backfill Service

Purpose
-------
Build KnowledgeEvidence and KnowledgeFacts for
historical InboxMessage records.

This service is reusable from:

- Django Management Commands
- Celery
- REST APIs
- Admin Actions
- Tenant onboarding
- Disaster recovery

It NEVER downloads emails again.

It processes existing InboxMessage records.
"""

from unittest import result, runner

from backend import settings
from inbox.models import InboxMessage

from knowledge.models import KnowledgeEvidence
from knowledge.services.message_processor import MessageProcessor
from knowledge.services.job_runner import JobRunner
from knowledge.models import KnowledgeJob
from django.utils import timezone

from knowledge.services.logger import (
    log_info,
    log_error,
)


class KnowledgeBackfillService:

    def __init__(self):

        self.processor = MessageProcessor()

    def process(
        self,
        *,
        organization=None,
        user=None,
        limit=None,
        force=False,
    ):

        queryset = InboxMessage.objects.select_related(
            "conversation",
            "organization",
            "user",
        )

        if organization:

            queryset = queryset.filter(
                organization=organization
            )

        if user:

            queryset = queryset.filter(
                user=user
            )

        queryset = queryset.order_by("received_at")

        if limit:

            queryset = queryset[:limit]

        runner = JobRunner(
            queryset.count(),
            checkpoint_interval=getattr(
                settings,
                "KNOWLEDGE_JOB_CHECKPOINT_INTERVAL",
                25,
            ),
        )

        runner = JobRunner(
            queryset.count(),
            checkpoint_interval=getattr(
                settings,
                "KNOWLEDGE_JOB_CHECKPOINT_INTERVAL",
                25,
            ),
        )

        runner = JobRunner(
            queryset.count(),
            checkpoint_interval=getattr(
                settings,
                "KNOWLEDGE_JOB_CHECKPOINT_INTERVAL",
                25,
            ),
        )

        # ----------------------------------------
        # Create Enterprise Job
        # ----------------------------------------

        job = KnowledgeJob.objects.create(
            organization=organization,
            user=user,
            job_type="BACKFILL",
            status="RUNNING",
        )

        log_info(
            "Knowledge backfill started",
            total=queryset.count(),
        )    

        for message in queryset:

            try:

                if not force:

                    exists = KnowledgeEvidence.objects.filter(
                        message=message
                    ).exists()

                    if exists:

                        runner.skip()
                        if runner.should_checkpoint:

                            job.processed = runner.processed
                            job.skipped = runner.skipped
                            job.failed = runner.failed

                            job.save(
                                update_fields=[
                                    "processed",
                                    "skipped",
                                    "failed",
                                ]
                            )

                            runner.checkpoint()

                        continue

                self.processor.process_message(
                    organization=message.organization,
                    message=message,
                    sender=message.sender,
                    subject=message.subject,
                    body=message.body,
                    source_channel=message.platform,
                )

                runner.success()

                if runner.should_checkpoint:

                    job.processed = runner.processed
                    job.skipped = runner.skipped
                    job.failed = runner.failed

                    job.save(
                        update_fields=[
                            "processed",
                            "skipped",
                            "failed",
                        ]
                    )

                    runner.checkpoint()

            except Exception as exc:

                log_error(
                    "Knowledge backfill failed",
                    message_id=message.id,
                    exception=str(exc),
                )

                runner.failure()
                if runner.should_checkpoint:

                    job.processed = runner.processed
                    job.skipped = runner.skipped
                    job.failed = runner.failed

                    job.save(
                        update_fields=[
                            "processed",
                            "skipped",
                            "failed",
                        ]
                    )

                    runner.checkpoint()

        result, metrics = runner.finish()

        log_info(
            "Knowledge backfill completed",
            processed=result.processed,
            skipped=result.skipped,
            failed=result.failed,
            duration=result.elapsed_seconds,
        )

        job.status = "COMPLETED"

        job.duration_seconds = result.elapsed_seconds

        job.completed_at = timezone.now()

        job.processed = result.processed

        job.skipped = result.skipped

        job.failed = result.failed

        job.save(
            update_fields=[
                "status",
                "duration_seconds",
                "completed_at",
                "processed",
                "skipped",
                "failed",
            ]
        )

        return {
            "processed": result.processed,
            "skipped": result.skipped,
            "failed": result.failed,
            "total": result.total,
            "elapsed": result.elapsed_seconds,
            "success_rate": metrics.success_rate,
            "throughput": metrics.throughput,
        }