"""
Enterprise Request Context

Carries request information across
the complete One UCH platform.

The object is immutable after creation.
"""

from dataclasses import dataclass
from typing import Optional
from uuid import uuid4
from datetime import datetime


@dataclass
class RequestContext:

    request_id: str

    correlation_id: str

    user: Optional[object]

    organization: Optional[object]

    tenant: Optional[object]

    ip_address: Optional[str]

    user_agent: Optional[str]

    path: str

    method: str

    started_at: Optional[datetime] = None

    execution_source: str = "http"

    security: Optional[object] = None

    @classmethod
    def empty(cls):

        request_id = str(uuid4())

        return cls(

            request_id=request_id,

            correlation_id=request_id,

            user=None,

            organization=None,

            tenant=None,

            ip_address=None,

            user_agent=None,

            path="",

            method="",

            started_at=datetime.utcnow(),

            execution_source="http",
        )