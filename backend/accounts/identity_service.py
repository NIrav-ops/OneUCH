
from dataclasses import (
    dataclass,
)
from datetime import (
    timedelta,
)
import hashlib
import secrets
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlsplit,
    urlunsplit,
)

from django.conf import (
    settings,
)
from django.core import (
    signing,
)
from django.core.exceptions import (
    ValidationError,
)
from django.core.validators import (
    validate_email,
)
from django.db import (
    IntegrityError,
    transaction,
)
from django.utils import (
    timezone,
)

from google.auth.transport.requests import (
    Request as GoogleAuthRequest,
)
from google.oauth2 import (
    id_token as google_id_token,
)

import jwt
import requests

from rest_framework_simplejwt.tokens import (
    RefreshToken,
)

from accounts.authentication import (
    get_active_membership,
)
from accounts.authentication_events import (
    record_authentication_success,
)
from accounts.models import (
    AUTH_METHOD_GOOGLE,
    AUTH_METHOD_MICROSOFT,
    ExternalIdentity,
    IdentityLoginGrant,
    User,
)


IDENTITY_PROVIDERS = (
    AUTH_METHOD_GOOGLE,
    AUTH_METHOD_MICROSOFT,
)

IDENTITY_STATE_SALT = (
    "accounts.identity.signin.state.v1"
)

IDENTITY_BROWSER_BINDING_COOKIE = (
    "oneuch_identity_txn"
)

IDENTITY_BROWSER_BINDING_COOKIE_PATH = (
    "/api/auth/identity/"
)

GENERIC_IDENTITY_ERROR = (
    "Unable to sign in with this identity provider."
)


class IdentityError(
    Exception,
):
    pass


class IdentityConfigurationError(
    IdentityError,
):
    pass


class IdentityAuthenticationError(
    IdentityError,
):
    pass


@dataclass(
    frozen=True,
)
class IdentityClaims:
    provider: str
    issuer: str
    subject: str
    email: str


def identity_feature_enabled():
    return bool(
        getattr(
            settings,
            "AUTH_IDENTITY_SIGNIN_ENABLED",
            False,
        )
    )


def _setting(
    name,
    default="",
):
    return str(
        getattr(
            settings,
            name,
            default,
        )
        or ""
    ).strip()


def _configured_value(
    value,
):
    normalized = str(
        value
        or ""
    ).strip()

    if not normalized:
        return False

    lowered = normalized.lower()

    return not (
        lowered == "replace-me"
        or
        lowered.startswith(
            "replace-with-"
        )
    )


def _provider_configuration(
    provider,
):
    if provider == AUTH_METHOD_GOOGLE:

        config = {
            "provider":
                AUTH_METHOD_GOOGLE,

            "client_id":
                _setting(
                    "GOOGLE_IDENTITY_CLIENT_ID"
                ),

            "client_secret":
                _setting(
                    "GOOGLE_IDENTITY_CLIENT_SECRET"
                ),

            "redirect_uri":
                _setting(
                    "GOOGLE_IDENTITY_REDIRECT_URI"
                ),

            "authorize_url":
                (
                    "https://accounts.google.com/"
                    "o/oauth2/v2/auth"
                ),

            "token_url":
                (
                    "https://oauth2.googleapis.com/token"
                ),

            "scope":
                "openid email profile",
        }

    elif provider == AUTH_METHOD_MICROSOFT:

        tenant = (
            _setting(
                "MICROSOFT_IDENTITY_TENANT_ID",
                "organizations",
            )
            or "organizations"
        )

        config = {
            "provider":
                AUTH_METHOD_MICROSOFT,

            "client_id":
                _setting(
                    "MICROSOFT_IDENTITY_CLIENT_ID"
                ),

            "client_secret":
                _setting(
                    "MICROSOFT_IDENTITY_CLIENT_SECRET"
                ),

            "redirect_uri":
                _setting(
                    "MICROSOFT_IDENTITY_REDIRECT_URI"
                ),

            "tenant":
                tenant,

            "authorize_url": (
                "https://login.microsoftonline.com/"
                + tenant
                + "/oauth2/v2.0/authorize"
            ),

            "token_url": (
                "https://login.microsoftonline.com/"
                + tenant
                + "/oauth2/v2.0/token"
            ),

            "jwks_url": (
                "https://login.microsoftonline.com/"
                "common/discovery/v2.0/keys"
            ),

            "scope":
                "openid email profile",
        }

    else:
        raise IdentityConfigurationError(
            GENERIC_IDENTITY_ERROR
        )

    for key in (
        "client_id",
        "client_secret",
        "redirect_uri",
    ):

        if not _configured_value(
            config[
                key
            ]
        ):
            raise IdentityConfigurationError(
                GENERIC_IDENTITY_ERROR
            )

    return config


def configured_identity_providers():

    if not identity_feature_enabled():
        return []

    providers = []

    for provider in IDENTITY_PROVIDERS:

        try:
            _provider_configuration(
                provider
            )

        except IdentityConfigurationError:
            continue

        providers.append(
            provider
        )

    return providers


def _require_feature():

    if not identity_feature_enabled():
        raise IdentityConfigurationError(
            GENERIC_IDENTITY_ERROR
        )


def identity_state_max_age_seconds():
    return int(
        getattr(
            settings,
            "AUTH_IDENTITY_STATE_MAX_AGE_SECONDS",
            600,
        )
    )


def create_identity_state(
    provider,
):
    _require_feature()

    _provider_configuration(
        provider
    )

    nonce = secrets.token_urlsafe(
        32
    )

    browser_binding = (
        secrets.token_urlsafe(
            32
        )
    )

    state = signing.dumps(
        {
            "purpose":
                "identity_signin",

            "provider":
                provider,

            "nonce":
                nonce,

            "browser_binding":
                browser_binding,
        },
        salt=IDENTITY_STATE_SALT,
        compress=True,
    )

    return (
        state,
        nonce,
        browser_binding,
    )


def resolve_identity_state(
    *,
    provider,
    state,
    browser_binding,
):
    if not state:
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    max_age = (
        identity_state_max_age_seconds()
    )

    try:
        payload = signing.loads(
            state,
            salt=IDENTITY_STATE_SALT,
            max_age=max_age,
        )

    except signing.BadSignature as exc:
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    if (
        payload.get(
            "purpose"
        )
        != "identity_signin"
    ):
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    if (
        payload.get(
            "provider"
        )
        != provider
    ):
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    nonce = str(
        payload.get(
            "nonce"
        )
        or ""
    ).strip()

    signed_browser_binding = str(
        payload.get(
            "browser_binding"
        )
        or ""
    ).strip()

    request_browser_binding = str(
        browser_binding
        or ""
    ).strip()

    if (
        not nonce
        or
        not signed_browser_binding
        or
        not request_browser_binding
        or
        not secrets.compare_digest(
            signed_browser_binding,
            request_browser_binding,
        )
    ):
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    return nonce


def build_authorization_url(
    provider,
):
    _require_feature()

    config = _provider_configuration(
        provider
    )

    (
        state,
        nonce,
        browser_binding,
    ) = create_identity_state(
        provider
    )

    params = {
        "client_id":
            config[
                "client_id"
            ],

        "redirect_uri":
            config[
                "redirect_uri"
            ],

        "response_type":
            "code",

        "scope":
            config[
                "scope"
            ],

        "state":
            state,

        "nonce":
            nonce,

        "prompt":
            "select_account",
    }

    if provider == AUTH_METHOD_MICROSOFT:
        params[
            "response_mode"
        ] = "query"

    authorization_url = (
        config[
            "authorize_url"
        ]
        + "?"
        + urlencode(
            params
        )
    )

    return (
        authorization_url,
        browser_binding,
    )


def _normalize_email(
    value,
):
    email = str(
        value
        or ""
    ).strip().lower()

    try:
        validate_email(
            email
        )

    except ValidationError as exc:
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        ) from exc

    return email


def validate_google_claims(
    claims,
    *,
    expected_nonce,
):
    issuer = str(
        claims.get(
            "iss"
        )
        or ""
    ).strip()

    if issuer not in {
        "accounts.google.com",
        "https://accounts.google.com",
    }:
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    subject = str(
        claims.get(
            "sub"
        )
        or ""
    ).strip()

    if not subject:
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    if (
        claims.get(
            "email_verified"
        )
        is not True
    ):
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    if (
        str(
            claims.get(
                "nonce"
            )
            or ""
        )
        != expected_nonce
    ):
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    return IdentityClaims(
        provider=AUTH_METHOD_GOOGLE,
        issuer=issuer,
        subject=subject,
        email=_normalize_email(
            claims.get(
                "email"
            )
        ),
    )


def validate_microsoft_claims(
    claims,
    *,
    expected_nonce,
):
    tenant_id = str(
        claims.get(
            "tid"
        )
        or ""
    ).strip()

    if not tenant_id:
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    expected_issuer = (
        "https://login.microsoftonline.com/"
        + tenant_id
        + "/v2.0"
    )

    issuer = str(
        claims.get(
            "iss"
        )
        or ""
    ).strip().rstrip(
        "/"
    )

    if (
        issuer
        != expected_issuer
    ):
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    subject = str(
        claims.get(
            "sub"
        )
        or ""
    ).strip()

    if not subject:
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    if (
        str(
            claims.get(
                "nonce"
            )
            or ""
        )
        != expected_nonce
    ):
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    email = (
        claims.get(
            "preferred_username"
        )
        or
        claims.get(
            "email"
        )
    )

    return IdentityClaims(
        provider=AUTH_METHOD_MICROSOFT,
        issuer=expected_issuer,
        subject=subject,
        email=_normalize_email(
            email
        ),
    )


def _provider_timeout():
    return float(
        getattr(
            settings,
            "AUTH_IDENTITY_PROVIDER_TIMEOUT_SECONDS",
            10,
        )
    )


def _exchange_google_identity(
    *,
    code,
    nonce,
):
    config = _provider_configuration(
        AUTH_METHOD_GOOGLE
    )

    try:
        response = requests.post(
            config[
                "token_url"
            ],
            data={
                "code":
                    code,

                "client_id":
                    config[
                        "client_id"
                    ],

                "client_secret":
                    config[
                        "client_secret"
                    ],

                "redirect_uri":
                    config[
                        "redirect_uri"
                    ],

                "grant_type":
                    "authorization_code",
            },
            timeout=_provider_timeout(),
        )

        response.raise_for_status()

        token_data = (
            response.json()
        )

        raw_id_token = (
            token_data.get(
                "id_token"
            )
        )

        if not raw_id_token:
            raise IdentityAuthenticationError(
                GENERIC_IDENTITY_ERROR
            )

        claims = (
            google_id_token
            .verify_oauth2_token(
                raw_id_token,
                GoogleAuthRequest(),
                config[
                    "client_id"
                ],
            )
        )

        return validate_google_claims(
            claims,
            expected_nonce=nonce,
        )

    except IdentityAuthenticationError:
        raise

    except (
        requests.RequestException,
        ValueError,
        TypeError,
    ) as exc:
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        ) from exc


def _exchange_microsoft_identity(
    *,
    code,
    nonce,
):
    config = _provider_configuration(
        AUTH_METHOD_MICROSOFT
    )

    try:
        response = requests.post(
            config[
                "token_url"
            ],
            data={
                "client_id":
                    config[
                        "client_id"
                    ],

                "client_secret":
                    config[
                        "client_secret"
                    ],

                "code":
                    code,

                "redirect_uri":
                    config[
                        "redirect_uri"
                    ],

                "grant_type":
                    "authorization_code",

                "scope":
                    config[
                        "scope"
                    ],
            },
            timeout=_provider_timeout(),
        )

        response.raise_for_status()

        token_data = (
            response.json()
        )

        raw_id_token = (
            token_data.get(
                "id_token"
            )
        )

        if not raw_id_token:
            raise IdentityAuthenticationError(
                GENERIC_IDENTITY_ERROR
            )

        unverified = jwt.decode(
            raw_id_token,
            options={
                "verify_signature":
                    False,

                "verify_exp":
                    False,

                "verify_aud":
                    False,
            },
        )

        tenant_id = str(
            unverified.get(
                "tid"
            )
            or ""
        ).strip()

        if not tenant_id:
            raise IdentityAuthenticationError(
                GENERIC_IDENTITY_ERROR
            )

        issuer = (
            "https://login.microsoftonline.com/"
            + tenant_id
            + "/v2.0"
        )

        jwks_client = (
            jwt.PyJWKClient(
                config[
                    "jwks_url"
                ]
            )
        )

        signing_key = (
            jwks_client
            .get_signing_key_from_jwt(
                raw_id_token
            )
        )

        claims = jwt.decode(
            raw_id_token,
            signing_key.key,
            algorithms=[
                "RS256",
            ],
            audience=(
                config[
                    "client_id"
                ]
            ),
            issuer=issuer,
        )

        return validate_microsoft_claims(
            claims,
            expected_nonce=nonce,
        )

    except IdentityAuthenticationError:
        raise

    except (
        requests.RequestException,
        jwt.PyJWTError,
        ValueError,
        TypeError,
    ) as exc:
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        ) from exc


def exchange_identity_code(
    *,
    provider,
    code,
    nonce,
):
    _require_feature()

    code = str(
        code
        or ""
    ).strip()

    if not code:
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    if provider == AUTH_METHOD_GOOGLE:
        return _exchange_google_identity(
            code=code,
            nonce=nonce,
        )

    if provider == AUTH_METHOD_MICROSOFT:
        return _exchange_microsoft_identity(
            code=code,
            nonce=nonce,
        )

    raise IdentityAuthenticationError(
        GENERIC_IDENTITY_ERROR
    )


def _assert_user_eligible(
    *,
    user,
    provider,
    email,
):
    if (
        user is None
        or not user.is_active
    ):
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    if (
        user.signup_method
        != provider
    ):
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    if (
        str(
            user.email
        ).strip().lower()
        !=
        str(
            email
        ).strip().lower()
    ):
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    if (
        get_active_membership(
            user
        )
        is None
    ):
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )


@transaction.atomic
def bind_identity_claims(
    claims,
):
    if (
        claims.provider
        not in IDENTITY_PROVIDERS
    ):
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    now = timezone.now()

    binding = (
        ExternalIdentity.objects
        .select_for_update()
        .select_related(
            "user"
        )
        .filter(
            provider=claims.provider,
            issuer=claims.issuer,
            subject=claims.subject,
        )
        .first()
    )

    if binding is not None:

        _assert_user_eligible(
            user=binding.user,
            provider=claims.provider,
            email=claims.email,
        )

        binding.last_authenticated_at = (
            now
        )

        binding.save(
            update_fields=[
                "last_authenticated_at",
            ]
        )

        return binding.user

    user = (
        User.objects
        .select_for_update()
        .filter(
            email__iexact=(
                claims.email
            )
        )
        .first()
    )

    _assert_user_eligible(
        user=user,
        provider=claims.provider,
        email=claims.email,
    )

    existing_user_binding = (
        ExternalIdentity.objects
        .select_for_update()
        .filter(
            user=user,
            provider=claims.provider,
        )
        .first()
    )

    if existing_user_binding is not None:
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    try:
        ExternalIdentity.objects.create(
            user=user,
            provider=claims.provider,
            issuer=claims.issuer,
            subject=claims.subject,
            email_at_binding=(
                claims.email
            ),
            last_authenticated_at=now,
        )

    except IntegrityError as exc:
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        ) from exc

    return user


def _grant_digest(
    raw_grant,
):
    return (
        hashlib.sha256(
            str(
                raw_grant
            ).encode(
                "utf-8"
            )
        )
        .hexdigest()
    )


def create_identity_login_grant(
    *,
    user,
    provider,
):
    if provider not in IDENTITY_PROVIDERS:
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    lifetime = int(
        getattr(
            settings,
            "AUTH_IDENTITY_GRANT_LIFETIME_SECONDS",
            120,
        )
    )

    expires_at = (
        timezone.now()
        +
        timedelta(
            seconds=lifetime
        )
    )

    for _ in range(
        5
    ):
        raw_grant = (
            secrets.token_urlsafe(
                32
            )
        )

        try:
            IdentityLoginGrant.objects.create(
                user=user,
                provider=provider,
                token_hash=(
                    _grant_digest(
                        raw_grant
                    )
                ),
                expires_at=expires_at,
            )

            return raw_grant

        except IntegrityError:
            continue

    raise IdentityAuthenticationError(
        GENERIC_IDENTITY_ERROR
    )


@transaction.atomic
def consume_identity_login_grant(
    raw_grant,
):
    raw_grant = str(
        raw_grant
        or ""
    ).strip()

    if (
        len(
            raw_grant
        )
        < 20
        or
        len(
            raw_grant
        )
        > 512
    ):
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    grant = (
        IdentityLoginGrant.objects
        .select_for_update()
        .select_related(
            "user"
        )
        .filter(
            token_hash=(
                _grant_digest(
                    raw_grant
                )
            )
        )
        .first()
    )

    now = timezone.now()

    if (
        grant is None
        or
        grant.used_at is not None
        or
        grant.expires_at <= now
    ):
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    user = grant.user

    if (
        not user.is_active
        or
        user.signup_method
        != grant.provider
        or
        get_active_membership(
            user
        )
        is None
    ):
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    if not (
        ExternalIdentity.objects
        .filter(
            user=user,
            provider=grant.provider,
        )
        .exists()
    ):
        raise IdentityAuthenticationError(
            GENERIC_IDENTITY_ERROR
        )

    grant.used_at = now

    grant.save(
        update_fields=[
            "used_at",
        ]
    )

    record_authentication_success(
        user=user,
        method=grant.provider,
    )

    refresh = (
        RefreshToken.for_user(
            user
        )
    )

    return {
        "access":
            str(
                refresh.access_token
            ),

        "refresh":
            str(
                refresh
            ),
    }


def build_frontend_login_redirect(
    **params,
):
    base = _setting(
        "ONEUCH_FRONTEND_LOGIN_URL",
        "http://localhost:5173/login",
    )

    parsed = urlsplit(
        base
    )

    if (
        parsed.scheme
        not in {
            "http",
            "https",
        }
        or
        not parsed.netloc
    ):
        raise IdentityConfigurationError(
            GENERIC_IDENTITY_ERROR
        )

    query = dict(
        parse_qsl(
            parsed.query,
            keep_blank_values=True,
        )
    )

    for key, value in (
        params.items()
    ):
        query[
            str(
                key
            )
        ] = str(
            value
        )

    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(
                query
            ),
            parsed.fragment,
        )
    )
