import base64


class AuthenticationProvider:
    """
    Applies authentication to outgoing HTTP requests.
    """

    def apply(self, request, configuration):

        auth = configuration.get("authentication")

        if not auth:
            return request

        auth_type = auth.get("type")

        headers = request.setdefault("headers", {})

        if auth_type == "bearer":

            token = auth.get("token", "")

            headers["Authorization"] = (
                f"Bearer {token}"
            )

        elif auth_type == "apikey":

            header = auth.get(
                "header",
                "X-API-Key",
            )

            headers[header] = auth.get(
                "key",
                "",
            )

        elif auth_type == "basic":

            username = auth.get("username", "")

            password = auth.get("password", "")

            encoded = base64.b64encode(
                f"{username}:{password}".encode()
            ).decode()

            headers["Authorization"] = (
                f"Basic {encoded}"
            )

        return request