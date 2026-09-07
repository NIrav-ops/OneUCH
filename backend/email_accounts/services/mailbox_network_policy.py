from dataclasses import (
    dataclass,
)

import ipaddress
import re
import socket
import ssl


class MailboxEndpointPolicyError(
    ValueError
):
    pass


SECURE_PORTS = {
    "imap": {
        993,
    },

    "smtp": {
        465,
    },
}


BLOCKED_HOST_SUFFIXES = {
    "localhost",
    "local",
    "localdomain",
    "internal",
    "lan",
    "home",
    "home.arpa",
}


HOST_LABEL = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$",
    re.IGNORECASE,
)


@dataclass(
    frozen=True,
)
class ValidatedMailboxEndpoint:

    host: str

    port: int

    resolved_addresses: tuple


def _policy_error(
    message,
):
    raise MailboxEndpointPolicyError(
        message
    )


def _normalize_host(
    value,
):
    if not isinstance(
        value,
        str,
    ):
        _policy_error(
            "Mailbox host must be a hostname or IP address."
        )

    host = value.strip()

    if not host:
        _policy_error(
            "Mailbox host is required."
        )

    if (
        "\x00" in host
        or
        any(
            character.isspace()
            for character
            in host
        )
    ):
        _policy_error(
            "Mailbox host is not permitted."
        )

    if (
        "://" in host
        or
        "/" in host
        or
        "\\" in host
        or
        "@" in host
        or
        "?" in host
        or
        "#" in host
    ):
        _policy_error(
            "Mailbox host is not permitted."
        )

    if (
        host.startswith(
            "["
        )
        and
        host.endswith(
            "]"
        )
    ):
        host = host[
            1:-1
        ]

    host = (
        host
        .rstrip(
            "."
        )
        .lower()
    )

    if not host:
        _policy_error(
            "Mailbox host is required."
        )

    try:
        literal = (
            ipaddress.ip_address(
                host
            )
        )

    except ValueError:
        literal = None

    if literal is not None:
        return (
            literal.compressed
        )

    if ":" in host:
        _policy_error(
            "Mailbox host must not include a port."
        )

    try:
        ascii_host = (
            host
            .encode(
                "idna"
            )
            .decode(
                "ascii"
            )
            .lower()
        )

    except UnicodeError:
        _policy_error(
            "Mailbox host is invalid."
        )

    if len(
        ascii_host
    ) > 253:
        _policy_error(
            "Mailbox host is invalid."
        )

    labels = ascii_host.split(
        "."
    )

    if (
        len(labels) < 2
        or
        any(
            not HOST_LABEL.fullmatch(
                label
            )
            for label
            in labels
        )
    ):
        _policy_error(
            "Mailbox host is invalid."
        )

    for suffix in (
        BLOCKED_HOST_SUFFIXES
    ):
        if (
            ascii_host
            ==
            suffix
            or
            ascii_host.endswith(
                "."
                + suffix
            )
        ):
            _policy_error(
                "Mailbox host is not permitted."
            )

    return ascii_host


def _normalize_port(
    value,
    *,
    protocol,
):
    if protocol not in (
        SECURE_PORTS
    ):
        _policy_error(
            "Unsupported mailbox protocol."
        )

    try:
        port = int(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        _policy_error(
            "Mailbox port is invalid."
        )

    if port not in (
        SECURE_PORTS[
            protocol
        ]
    ):
        if protocol == "imap":
            _policy_error(
                "Secure IMAP currently requires port 993."
            )

        _policy_error(
            "Secure SMTP currently requires port 465."
        )

    return port


def _ensure_public_address(
    value,
):
    try:
        address = (
            ipaddress.ip_address(
                value
            )
        )

    except ValueError:
        _policy_error(
            "Mailbox host resolved to an invalid address."
        )

    if not address.is_global:
        _policy_error(
            "Mailbox host resolved to a non-public address."
        )

    return address.compressed


def validate_mailbox_endpoint(
    *,
    host,
    port,
    protocol,
    resolver=None,
):
    """
    Validate a mailbox network destination before socket I/O.

    Policy:
    - hostname only, never a URL/userinfo/path
    - implicit TLS ports only for the currently implemented
      IMAP4_SSL / SMTP_SSL transports
    - literal IPs must be globally routable
    - every current DNS answer must be globally routable

    DNS validation is repeated immediately before provider
    socket creation by the IMAP/SMTP service. This prevents
    persisted unsafe destinations from bypassing the API gate.
    """

    normalized_host = (
        _normalize_host(
            host
        )
    )

    normalized_port = (
        _normalize_port(
            port,
            protocol=protocol,
        )
    )

    try:
        literal = (
            ipaddress.ip_address(
                normalized_host
            )
        )

    except ValueError:
        literal = None

    if literal is not None:

        public_address = (
            _ensure_public_address(
                literal.compressed
            )
        )

        return (
            ValidatedMailboxEndpoint(
                host=normalized_host,
                port=normalized_port,
                resolved_addresses=(
                    public_address,
                ),
            )
        )

    resolver_function = (
        resolver
        or
        socket.getaddrinfo
    )

    try:
        answers = (
            resolver_function(
                normalized_host,
                normalized_port,
                socket.AF_UNSPEC,
                socket.SOCK_STREAM,
            )
        )

    except (
        socket.gaierror,
        OSError,
    ) as exc:
        raise MailboxEndpointPolicyError(
            "Mailbox host could not be resolved."
        ) from exc

    addresses = []

    for answer in (
        answers
        or []
    ):
        try:
            sockaddr = answer[
                4
            ]

            raw_address = (
                sockaddr[
                    0
                ]
            )

        except (
            IndexError,
            TypeError,
        ):
            _policy_error(
                "Mailbox host resolution was invalid."
            )

        normalized_address = (
            _ensure_public_address(
                raw_address
            )
        )

        if (
            normalized_address
            not in addresses
        ):
            addresses.append(
                normalized_address
            )

    if not addresses:
        _policy_error(
            "Mailbox host could not be resolved."
        )

    return (
        ValidatedMailboxEndpoint(
            host=normalized_host,
            port=normalized_port,
            resolved_addresses=tuple(
                addresses
            ),
        )
    )



def connect_validated_mailbox_endpoint(
    *,
    endpoint,
    timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
    source_address=None,
):
    """
    Connect only to an IP address already validated by the
    mailbox endpoint policy.

    The original hostname is deliberately NOT passed to
    socket.create_connection(), preventing a second DNS lookup
    between policy validation and TCP connection.
    """

    last_error = None

    for address in (
        endpoint.resolved_addresses
    ):
        try:
            target = (
                address,
                endpoint.port,
            )

            if (
                timeout
                is
                socket._GLOBAL_DEFAULT_TIMEOUT
                and
                source_address is None
            ):
                return (
                    socket.create_connection(
                        target
                    )
                )

            if source_address is None:
                return (
                    socket.create_connection(
                        target,
                        timeout,
                    )
                )

            return (
                socket.create_connection(
                    target,
                    timeout,
                    source_address,
                )
            )

        except OSError as exc:
            last_error = exc

    raise OSError(
        "Unable to connect to validated mailbox endpoint."
    ) from last_error


def create_verified_tls_context():
    """
    Explicitly require normal CA validation and hostname
    verification for Other Work Email TLS sessions.
    """

    context = (
        ssl.create_default_context()
    )

    if not context.check_hostname:
        raise RuntimeError(
            "Mailbox TLS hostname verification is disabled."
        )

    if (
        context.verify_mode
        !=
        ssl.CERT_REQUIRED
    ):
        raise RuntimeError(
            "Mailbox TLS certificate verification is disabled."
        )

    return context
