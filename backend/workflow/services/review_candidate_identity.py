import hashlib
import re
import unicodedata
from email.utils import parseaddr


SHARED_MAIL_DOMAINS = frozenset({
    "gmail.com",
    "googlemail.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "yahoo.com",
    "yahoo.co.in",
    "icloud.com",
    "me.com",
    "aol.com",
    "proton.me",
    "protonmail.com",
})


def normalize_sender_email(
    sender,
):
    address = parseaddr(
        str(sender or "")
    )[1].strip().lower()

    return address


def normalize_source_domain(
    sender,
):
    """
    Return a conservative normalized sender domain.

    Different corporate domains are deliberately kept
    separate. BusinessIdentity may unify verified aliases
    later, but this layer does not guess.
    """

    address = normalize_sender_email(
        sender
    )

    if "@" not in address:
        return ""

    domain = (
        address
        .rsplit("@", 1)[1]
        .strip()
        .strip(".")
        .lower()
    )

    if not domain:
        return ""

    try:
        domain = (
            domain
            .encode("idna")
            .decode("ascii")
        )
    except UnicodeError:
        pass

    return domain


def is_shared_mail_domain(
    domain,
):
    return (
        str(domain or "")
        .strip()
        .lower()
        in SHARED_MAIL_DOMAINS
    )


def normalize_candidate_basis(
    *,
    title,
    evidence,
):
    """
    Conservative near-exact request identity.

    Evidence is preferred because it is directly grounded
    in the source communication.

    Only Unicode, case and whitespace normalization is used.
    No fuzzy or semantic dedupe is performed.
    """

    value = (
        str(evidence or "").strip()
        or
        str(title or "").strip()
    )

    if not value:
        return ""

    value = unicodedata.normalize(
        "NFKC",
        value,
    ).casefold()

    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    return value


def build_candidate_fingerprint(
    *,
    title,
    evidence,
    source_identity="",
):
    """
    Build the request fingerprint.

    For corporate domains source_identity is blank, so
    different senders at the same domain can collapse into
    one candidate.

    For shared/public mail domains source_identity contains
    the exact sender email, preventing unrelated Gmail /
    Outlook / Yahoo users from being merged.
    """

    basis = normalize_candidate_basis(
        title=title,
        evidence=evidence,
    )

    if not basis:
        return ""

    source_identity = (
        str(source_identity or "")
        .strip()
        .casefold()
    )

    if source_identity:
        basis = (
            source_identity
            + "\n"
            + basis
        )

    return hashlib.sha256(
        basis.encode("utf-8")
    ).hexdigest()
