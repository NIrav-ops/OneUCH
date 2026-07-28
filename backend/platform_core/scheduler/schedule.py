from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Schedule:

    id: str

    name: str

    interval: int

    job_name: str

    payload: dict

    enabled: bool = True

    created_at: datetime = field(
        default_factory=datetime.utcnow,
    )