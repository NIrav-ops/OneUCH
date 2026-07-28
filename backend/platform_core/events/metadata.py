from dataclasses import dataclass


@dataclass
class EventMetadata:

    source: str

    organization: int | None = None

    user: int | None = None

    correlation_id: str | None = None