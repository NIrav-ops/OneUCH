"""
Enterprise Job Runner

Reusable execution framework for long-running jobs.

Responsibilities

- Progress reporting
- Elapsed time
- Success count
- Failure count
- Skip count
- Resume support (future)
"""

import time

from dataclasses import (
    dataclass,
)

from knowledge.services.metrics import (
    KnowledgeMetrics,
)


@dataclass
class JobResult:

    processed: int = 0

    skipped: int = 0

    failed: int = 0

    total: int = 0

    elapsed_seconds: float = 0


class JobRunner:

    def __init__(
        self,
        total,
        checkpoint_interval=25,
    ):

        self.total = total

        self.processed = 0

        self.skipped = 0

        self.failed = 0

        self.started = time.time()

        self.checkpoint_interval = (
            checkpoint_interval
        )

        self.last_checkpoint = 0


    def success(
        self,
    ):

        self.processed += 1

        self.print_progress()


    def skip(
        self,
    ):

        self.skipped += 1

        self.print_progress()


    def failure(
        self,
    ):

        self.failed += 1

        self.print_progress()


    @property
    def completed(
        self,
    ):

        return (
            self.processed
            +
            self.skipped
            +
            self.failed
        )


    @property
    def should_checkpoint(
        self,
    ):

        return (
            self.completed
            -
            self.last_checkpoint
        ) >= (
            self.checkpoint_interval
        )


    @property
    def percentage(
        self,
    ):

        if self.total == 0:
            return 100

        return round(
            (
                self.completed
                /
                self.total
            )
            *
            100,
            2,
        )


    def elapsed(
        self,
    ):

        return round(
            time.time()
            -
            self.started,
            2,
        )


    def print_progress(
        self,
    ):

        print(
            f"[{self.completed}/{self.total}] "
            f"{self.percentage}% "
            f"| OK:{self.processed} "
            f"| SKIP:{self.skipped} "
            f"| FAIL:{self.failed}"
        )


    def checkpoint(
        self,
    ):

        self.last_checkpoint = (
            self.completed
        )


    def finish(
        self,
    ):

        result = JobResult(
            processed=(
                self.processed
            ),
            skipped=(
                self.skipped
            ),
            failed=(
                self.failed
            ),
            total=(
                self.total
            ),
            elapsed_seconds=(
                self.elapsed()
            ),
        )

        metrics = KnowledgeMetrics(
            processed=(
                result.processed
            ),
            skipped=(
                result.skipped
            ),
            failed=(
                result.failed
            ),
            duration_seconds=(
                result.elapsed_seconds
            ),
        )

        return (
            result,
            metrics,
        )
