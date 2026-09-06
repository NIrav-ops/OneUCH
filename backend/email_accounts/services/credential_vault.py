
import base64
import hashlib

from cryptography.fernet import (
    Fernet,
    InvalidToken,
)

from django.conf import (
    settings,
)


class CredentialVaultError(
    RuntimeError
):
    pass


def _fernet():
    secret = str(
        settings.SECRET_KEY
        or ""
    )

    if not secret:
        raise CredentialVaultError(
            "Credential vault key is unavailable."
        )

    material = (
        "oneuch-mail-credential-v1:"
        + secret
    ).encode(
        "utf-8"
    )

    key = (
        base64.urlsafe_b64encode(
            hashlib.sha256(
                material
            ).digest()
        )
    )

    return Fernet(
        key
    )


def encrypt_credential(
    plaintext,
):
    if plaintext is None:
        return None

    plaintext = str(
        plaintext
    )

    if not plaintext:
        return None

    return (
        _fernet()
        .encrypt(
            plaintext.encode(
                "utf-8"
            )
        )
        .decode(
            "ascii"
        )
    )


def decrypt_credential(
    ciphertext,
):
    if not ciphertext:
        return None

    try:
        return (
            _fernet()
            .decrypt(
                str(
                    ciphertext
                ).encode(
                    "ascii"
                )
            )
            .decode(
                "utf-8"
            )
        )

    except (
        InvalidToken,
        UnicodeDecodeError,
        ValueError,
    ) as exc:

        raise CredentialVaultError(
            "Mailbox credential could not be decrypted."
        ) from exc
