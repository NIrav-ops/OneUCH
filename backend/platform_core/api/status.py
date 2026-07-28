"""
Enterprise API Status Constants

Used throughout One UCH.

Do not hardcode HTTP messages
inside API views.
"""

SUCCESS = "success"

FAILED = "failed"

ERROR = "error"

WARNING = "warning"

INFO = "info"


MESSAGE_SUCCESS = "Request completed successfully."

MESSAGE_CREATED = "Resource created successfully."

MESSAGE_UPDATED = "Resource updated successfully."

MESSAGE_DELETED = "Resource deleted successfully."

MESSAGE_NOT_FOUND = "Resource not found."

MESSAGE_UNAUTHORIZED = "Authentication required."

MESSAGE_FORBIDDEN = "Permission denied."

MESSAGE_BAD_REQUEST = "Invalid request."

MESSAGE_SERVER_ERROR = "Internal server error."