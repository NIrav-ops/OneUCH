from rest_framework.response import Response
from rest_framework import status


def api_success(data=None, message=None, status_code=status.HTTP_200_OK):
    return Response(
        {
            "success": True,
            "data": data,
            "message": message,
        },
        status=status_code,
    )


def api_error(message, status_code=status.HTTP_400_BAD_REQUEST):
    return Response(
        {
            "success": False,
            "data": None,
            "message": message,
        },
        status=status_code,
    )
