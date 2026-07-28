from dataclasses import dataclass


@dataclass
class EventContext:

    organization=None

    user=None

    request_id=None

    correlation_id=None