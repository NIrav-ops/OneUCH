from dataclasses import (
    dataclass,
    field,
)

from django.utils import timezone


@dataclass
class HealthStatus:

    service: str

    status: str

    details: dict

    checked_at: object = field(
        default_factory=timezone.now
    )
