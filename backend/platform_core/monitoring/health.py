from dataclasses import dataclass
from datetime import datetime


@dataclass
class HealthStatus:

    service: str

    status: str

    details: dict

    checked_at: datetime = datetime.utcnow()