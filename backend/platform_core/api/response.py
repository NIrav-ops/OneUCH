from datetime import datetime

from rest_framework.response import Response

from rest_framework import status

from platform_core.api.metadata import (
    ResponseMetadata,
)

class APIResponse:

    """
    Enterprise Standard API Response

    Every REST API in One UCH
    should return this structure.

    {
        success,
        message,
        data,
        errors,
        meta
    }
    """

    @staticmethod
    def build(

        *,

        success=True,

        message="",

        data=None,

        errors=None,

        meta=None,

        status_code=status.HTTP_200_OK,

    ):

        if errors is None:

            errors = []

        if meta is None:

            meta = ResponseMetadata.build()

    
        metadata = ResponseMetadata.build()

        metadata.update(

            meta,

        )

        return Response(

            {

                "success": success,

                "message": message,

                "data": data,

                "errors": errors,

                "meta": metadata,

            },

            status=status_code,

        )