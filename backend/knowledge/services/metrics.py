"""
Enterprise Knowledge Metrics Service
"""

from dataclasses import dataclass


@dataclass
class KnowledgeMetrics:

    processed: int = 0
    skipped: int = 0
    failed: int = 0
    duration_seconds: float = 0.0

    @property
    def success_rate(self):

        total = self.processed + self.failed

        if total == 0:
            return 100.0

        return round(
            (self.processed / total) * 100,
            2,
        )

    @property
    def throughput(self):

        if self.duration_seconds == 0:
            return 0

        return round(
            self.processed / self.duration_seconds,
            2,
        )
    
