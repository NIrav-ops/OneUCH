from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BackgroundJob:

    id: str

    name: str

    payload: dict

    retries: int = 0

    created_at: datetime = field(
        default_factory=datetime.utcnow,
    )