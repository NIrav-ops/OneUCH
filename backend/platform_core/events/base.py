from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4


@dataclass
class DomainEvent:

    name: str

    payload: dict

    timestamp: datetime = datetime.utcnow()

    event_id: str = ""

    def __post_init__(self):

        if not self.event_id:

            self.event_id = str(
                uuid4(),
            )