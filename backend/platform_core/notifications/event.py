from dataclasses import dataclass
from datetime import datetime


@dataclass
class NotificationEvent:

    title: str

    message: str

    event_name: str

    payload: dict

    timestamp: datetime = datetime.utcnow()