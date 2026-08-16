import requests


class HTTPTransport:
    """
    Low-level HTTP transport.

    Responsible only for performing HTTP requests.

    No workflow logic belongs here.
    """

    DEFAULT_TIMEOUT = 30

    def send(
        self,
        method,
        url,
        headers=None,
        params=None,
        json=None,
        timeout=None,
    ):

        response = requests.request(
            method=method,
            url=url,
            headers=headers or {},
            params=params,
            json=json,
            timeout=timeout or self.DEFAULT_TIMEOUT,
        )

        return response