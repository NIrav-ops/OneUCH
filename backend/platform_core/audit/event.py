from dataclasses import dataclass
from datetime import datetime


@dataclass
class AuditEvent:

    event_name: str

    payload: dict

    timestamp: datetime = datetime.utcnow()