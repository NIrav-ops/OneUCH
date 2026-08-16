class ResponseParser:
    """
    Converts an HTTP response into
    workflow-friendly output.
    """

    def parse(
        self,
        response,
    ):

        try:

            body = response.json()

        except Exception:

            body = response.text

        return {

            "status_code": response.status_code,

            "headers": dict(
                response.headers
            ),

            "body": body,

            "success": (
                response.status_code < 400
            ),
        }