"""
Enterprise Knowledge Backfill Service

Purpose
-------
Build KnowledgeEvidence and KnowledgeFacts for
historical InboxMessage records.

This service NEVER downloads email again.

It processes existing governed InboxMessage records.
"""

import logging

from django.conf import (
    settings,
)

from django.utils import (
    timezone,
)

from inbox.models import (
    InboxMessage,
)

from knowledge.models import (
    KnowledgeEvidence,
    KnowledgeJob,
)

from knowledge.services.message_processor import (
    MessageProcessor,
)

from knowledge.services.job_runner import (
    JobRunner,
)

from knowledge.services.logger import (
    log_info,
    log_error,
)


class KnowledgeBackfillService:

    def __init__(
        self,
    ):

        self.processor = (
            MessageProcessor()
        )


    @staticmethod
    def _coverage_rate(
        *,
        matched,
        unmatched,
    ):

        total = (
            matched
            +
            unmatched
        )

        if total == 0:
            return 100.0

        return round(
            (
                matched
                /
                total
            )
            *
            100,
            2,
        )


    @staticmethod
    def _queryset(
        *,
        organization=None,
        user=None,
        limit=None,
    ):

        queryset = (
            InboxMessage.objects
            .select_related(
                "conversation",
                "organization",
                "user",
            )
            .filter(
                is_draft=False
            )
        )

        if organization:

            queryset = (
                queryset.filter(
                    organization=(
                        organization
                    )
                )
            )

        if user:

            queryset = (
                queryset.filter(
                    user=user
                )
            )

        queryset = (
            queryset.order_by(
                "received_at",
                "id",
            )
        )

        if limit:

            queryset = (
                queryset[
                    :limit
                ]
            )

        return queryset


    def preview(
        self,
        *,
        organization=None,
        user=None,
        limit=None,
    ):
        """
        Read-only resolution preview.

        Creates no KnowledgeJob, KnowledgeEvidence,
        KnowledgeFact or relationship rows.
        """

        queryset = (
            self._queryset(
                organization=organization,
                user=user,
                limit=limit,
            )
        )

        matched = 0

        unmatched = 0

        ambiguous = 0


        knowledge_logger = (
            logging.getLogger(
                "knowledge"
            )
        )

        previous_level = (
            knowledge_logger.level
        )

        knowledge_logger.setLevel(
            logging.WARNING
        )


        try:

            for message in (
                queryset.iterator()
            ):

                resolution = (
                    self.processor
                    .resolve_message(
                        organization=(
                            message.organization
                        ),
                        message=message,
                        sender=(
                            message.sender
                        ),
                        subject=(
                            message.subject
                        ),
                        body=(
                            message.body
                        ),
                    )
                )

                if resolution[
                    "matched"
                ]:

                    matched += 1

                else:

                    unmatched += 1

                    if resolution.get(
                        "ambiguous",
                        False,
                    ):

                        ambiguous += 1


        finally:

            knowledge_logger.setLevel(
                previous_level
            )


        return {
            "total":
                queryset.count(),

            "matched":
                matched,

            "unmatched":
                unmatched,

            "ambiguous":
                ambiguous,

            "coverage_rate":
                self._coverage_rate(
                    matched=matched,
                    unmatched=unmatched,
                ),
        }


    def process(
        self,
        *,
        organization=None,
        user=None,
        limit=None,
        force=False,
    ):

        queryset = (
            self._queryset(
                organization=organization,
                user=user,
                limit=limit,
            )
        )


        runner = JobRunner(
            queryset.count(),
            checkpoint_interval=(
                getattr(
                    settings,
                    "KNOWLEDGE_JOB_CHECKPOINT_INTERVAL",
                    25,
                )
            ),
        )


        job = (
            KnowledgeJob.objects.create(
                organization=organization,
                user=user,
                job_type="BACKFILL",
                status="RUNNING",
            )
        )


        matched = 0

        unmatched = 0

        ambiguous = 0


        def coverage_rate():
            return (
                self._coverage_rate(
                    matched=matched,
                    unmatched=unmatched,
                )
            )


        def save_checkpoint():

            job.processed = (
                runner.processed
            )

            job.skipped = (
                runner.skipped
            )

            job.failed = (
                runner.failed
            )

            job.metadata = {
                "matched":
                    matched,

                "unmatched":
                    unmatched,

                "ambiguous":
                    ambiguous,

                "coverage_rate":
                    coverage_rate(),
            }

            job.save(
                update_fields=[
                    "processed",
                    "skipped",
                    "failed",
                    "metadata",
                ]
            )

            runner.checkpoint()


        log_info(
            "Knowledge backfill started",
            total=queryset.count(),
        )


        for message in queryset:

            try:

                if not force:

                    exists = (
                        KnowledgeEvidence.objects
                        .filter(
                            message=message
                        )
                        .exists()
                    )

                    if exists:

                        runner.skip()

                        if (
                            runner.should_checkpoint
                        ):

                            save_checkpoint()

                        continue


                result = (
                    self.processor
                    .process_message(
                        organization=(
                            message.organization
                        ),
                        message=message,
                        sender=(
                            message.sender
                        ),
                        subject=(
                            message.subject
                        ),
                        body=(
                            message.body
                        ),
                        source_channel=(
                            message.platform
                        ),
                    )
                )


                if result[
                    "matched"
                ]:

                    matched += 1

                else:

                    unmatched += 1

                    if result.get(
                        "ambiguous",
                        False,
                    ):

                        ambiguous += 1


                runner.success()


                if (
                    runner.should_checkpoint
                ):

                    save_checkpoint()


            except Exception as exc:

                log_error(
                    "Knowledge backfill failed",
                    message_id=(
                        message.id
                    ),
                    exception=(
                        str(
                            exc
                        )
                    ),
                )

                runner.failure()

                if (
                    runner.should_checkpoint
                ):

                    save_checkpoint()


        result, metrics = (
            runner.finish()
        )


        final_coverage = (
            coverage_rate()
        )


        log_info(
            "Knowledge backfill completed",
            processed=(
                result.processed
            ),
            matched=matched,
            unmatched=unmatched,
            ambiguous=ambiguous,
            skipped=(
                result.skipped
            ),
            failed=(
                result.failed
            ),
            coverage_rate=(
                final_coverage
            ),
            duration=(
                result.elapsed_seconds
            ),
        )


        job.status = (
            "FAILED"
            if result.failed
            else "COMPLETED"
        )

        job.duration_seconds = (
            result.elapsed_seconds
        )

        job.completed_at = (
            timezone.now()
        )

        job.processed = (
            result.processed
        )

        job.skipped = (
            result.skipped
        )

        job.failed = (
            result.failed
        )

        job.metadata = {
            "matched":
                matched,

            "unmatched":
                unmatched,

            "ambiguous":
                ambiguous,

            "coverage_rate":
                final_coverage,
        }


        job.save(
            update_fields=[
                "status",
                "duration_seconds",
                "completed_at",
                "processed",
                "skipped",
                "failed",
                "metadata",
            ]
        )


        return {
            "processed":
                result.processed,

            "matched":
                matched,

            "unmatched":
                unmatched,

            "ambiguous":
                ambiguous,

            "skipped":
                result.skipped,

            "failed":
                result.failed,

            "total":
                result.total,

            "elapsed":
                result.elapsed_seconds,

            "success_rate":
                metrics.success_rate,

            "throughput":
                metrics.throughput,

            "coverage_rate":
                final_coverage,

            "job_status":
                job.status,
        }
