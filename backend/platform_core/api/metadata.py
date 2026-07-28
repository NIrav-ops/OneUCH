"""
Enterprise Response Metadata

Provides metadata injected into every
API response.
"""

from datetime import datetime
import uuid

from platform_core.api.versioning import (
    CURRENT_VERSION,
)


class ResponseMetadata:

    @staticmethod
    def build(

        *,

        pagination=None,

    ):

        return {

            "request_id": str(

                uuid.uuid4(),

            ),

            "timestamp": datetime.utcnow().isoformat(),

            "server_time": datetime.utcnow().isoformat(),

            "api_version": CURRENT_VERSION.short,

            "api_version_full": CURRENT_VERSION.full,

            "pagination": pagination or {},

        }