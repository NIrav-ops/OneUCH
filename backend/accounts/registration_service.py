from datetime import (
    datetime,
)

from uuid import (
    uuid4,
)

from django.conf import (
    settings,
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

from accounts.models import (
    AUTH_METHOD_GOOGLE,
    AUTH_METHOD_MICROSOFT,
    ExternalIdentity,
    REGISTRATION_STATUS_APPROVED,
    REGISTRATION_STATUS_PENDING,
    REGISTRATION_STATUS_REJECTED,
    RegistrationRequest,
    User,
)

from inbox.models import (
    AuditLog,
    Organization,
    OrganizationUser,
)


SUPPORTED_REGISTRATION_PROVIDERS = {
    AUTH_METHOD_GOOGLE,
    AUTH_METHOD_MICROSOFT,
}


class RegistrationLifecycleError(
    Exception,
):
    pass


class RegistrationValidationError(
    RegistrationLifecycleError,
):
    pass


class RegistrationConflictError(
    RegistrationLifecycleError,
):
    pass


class RegistrationNotFoundError(
    RegistrationLifecycleError,
):
    pass


class RegistrationTransitionError(
    RegistrationLifecycleError,
):
    pass


class RegistrationReviewAuthorizationError(
    RegistrationLifecycleError,
):
    pass


def _required_text(
    value,
    *,
    field,
    max_length,
):
    normalized = str(
        value
        or ""
    ).strip()

    if (
        not normalized
        or
        len(normalized) > max_length
    ):
        raise RegistrationValidationError(
            "Invalid "
            + field
            + "."
        )

    return normalized


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
        raise RegistrationValidationError(
            "Invalid registration identity."
        ) from exc

    return email


def _normalize_provider(
    value,
):
    provider = str(
        value
        or ""
    ).strip().lower()

    if (
        provider
        not in
        SUPPORTED_REGISTRATION_PROVIDERS
    ):
        raise RegistrationValidationError(
            "Unsupported registration provider."
        )

    return provider


def _normalize_consent_time(
    value,
):
    if not isinstance(
        value,
        datetime,
    ):
        raise RegistrationValidationError(
            "Consent timestamp is required."
        )

    if timezone.is_naive(
        value
    ):
        raise RegistrationValidationError(
            "Consent timestamp must be timezone-aware."
        )

    return value


def _registration_region(
    value,
):
    region = str(
        value
        or getattr(
            settings,
            "ONEUCH_REGION",
            "",
        )
        or ""
    ).strip()

    if len(region) > 64:
        raise RegistrationValidationError(
            "Invalid requested region."
        )

    return region


def _audit_registration(
    *,
    registration,
    action,
    actor,
):
    """
    Record only registration provenance.

    Do not duplicate email, organization name, provider tokens,
    mailbox addresses, message content or review free-text into
    audit metadata.
    """

    AuditLog.objects.create(
        user=actor,
        organization=(
            registration.organization
        ),
        action=action,
        metadata={
            "registration_id":
                registration.public_id,

            "subject_user_id":
                registration.user.public_id,

            "provider":
                registration.provider,

            "status":
                registration.status,
        },
    )


def _existing_registration_for_binding(
    *,
    binding,
    email,
    provider,
):
    user = binding.user

    if (
        str(
            binding.email_at_binding
        ).strip().lower()
        != email
        or
        str(
            user.email
        ).strip().lower()
        != email
        or
        user.signup_method
        != provider
    ):
        raise RegistrationConflictError(
            "Registration identity conflict."
        )

    registration = (
        RegistrationRequest.objects
        .select_related(
            "user",
            "organization",
        )
        .filter(
            user=user,
            provider=provider,
        )
        .first()
    )

    if registration is None:
        raise RegistrationConflictError(
            "Registration identity conflict."
        )

    return registration


def submit_registration_request(
    *,
    provider,
    issuer,
    subject,
    email,
    organization_name,
    privacy_notice_version,
    terms_version,
    consent_recorded_at,
    requested_region="",
):
    """
    Create the fail-closed identity + tenant registration shell.

    This function assumes the caller has already verified the
    provider claims. D3B will connect the existing OIDC callback
    to this service.

    No provider token is accepted or persisted.
    """

    provider = _normalize_provider(
        provider
    )

    issuer = _required_text(
        issuer,
        field="issuer",
        max_length=255,
    )

    subject = _required_text(
        subject,
        field="subject",
        max_length=255,
    )

    email = _normalize_email(
        email
    )

    organization_name = (
        _required_text(
            organization_name,
            field="organization name",
            max_length=255,
        )
    )

    privacy_notice_version = (
        _required_text(
            privacy_notice_version,
            field="privacy notice version",
            max_length=64,
        )
    )

    terms_version = (
        _required_text(
            terms_version,
            field="terms version",
            max_length=64,
        )
    )

    consent_recorded_at = (
        _normalize_consent_time(
            consent_recorded_at
        )
    )

    requested_region = (
        _registration_region(
            requested_region
        )
    )


    try:

        with transaction.atomic():

            binding = (
                ExternalIdentity.objects
                .select_for_update()
                .select_related(
                    "user"
                )
                .filter(
                    provider=provider,
                    issuer=issuer,
                    subject=subject,
                )
                .first()
            )


            if binding is not None:

                registration = (
                    _existing_registration_for_binding(
                        binding=binding,
                        email=email,
                        provider=provider,
                    )
                )

                return (
                    registration,
                    False,
                )


            # Never link a new provider identity merely because
            # an email address matches an existing One UCH user.
            if (
                User.objects
                .select_for_update()
                .filter(
                    email__iexact=email
                )
                .exists()
            ):
                raise RegistrationConflictError(
                    "Registration identity conflict."
                )


            user = (
                User.objects
                .create_user(
                    email=email,
                    password=None,
                    signup_method=provider,
                    is_active=False,
                )
            )


            organization = (
                Organization.objects
                .create(
                    name=(
                        organization_name
                    ),
                    slug=(
                        "pending-"
                        + uuid4().hex
                    ),
                    is_active=False,
                )
            )


            OrganizationUser.objects.create(
                user=user,
                organization=organization,
                role="owner",
            )


            ExternalIdentity.objects.create(
                user=user,
                provider=provider,
                issuer=issuer,
                subject=subject,
                email_at_binding=email,
                last_authenticated_at=(
                    timezone.now()
                ),
            )


            registration = (
                RegistrationRequest.objects
                .create(
                    user=user,
                    organization=(
                        organization
                    ),
                    provider=provider,
                    status=(
                        REGISTRATION_STATUS_PENDING
                    ),
                    organization_name=(
                        organization_name
                    ),
                    privacy_notice_version=(
                        privacy_notice_version
                    ),
                    terms_version=(
                        terms_version
                    ),
                    consent_recorded_at=(
                        consent_recorded_at
                    ),
                    requested_region=(
                        requested_region
                    ),
                )
            )


            _audit_registration(
                registration=registration,
                action=(
                    "REGISTRATION_REQUESTED"
                ),
                actor=user,
            )


            return (
                registration,
                True,
            )


    except RegistrationLifecycleError:
        raise

    except IntegrityError as exc:
        raise RegistrationConflictError(
            "Registration identity conflict."
        ) from exc


def _require_platform_reviewer(
    reviewer,
):
    if (
        reviewer is None
        or
        not reviewer.is_active
        or
        not reviewer.is_staff
    ):
        raise (
            RegistrationReviewAuthorizationError(
                "Platform staff review required."
            )
        )


def _locked_registration(
    public_id,
):
    registration = (
        RegistrationRequest.objects
        .select_for_update()
        .select_related(
            "user",
            "organization",
        )
        .filter(
            public_id=(
                str(
                    public_id
                    or ""
                ).strip()
            )
        )
        .first()
    )

    if registration is None:
        raise RegistrationNotFoundError(
            "Registration request not found."
        )

    return registration


def _assert_pending_integrity(
    registration,
):
    user = registration.user
    organization = (
        registration.organization
    )

    if (
        registration.status
        !=
        REGISTRATION_STATUS_PENDING
    ):
        raise RegistrationTransitionError(
            "Registration is not pending."
        )


    # Pending registration must remain fail-closed.
    if (
        user.is_active
        or
        organization.is_active
    ):
        raise RegistrationTransitionError(
            "Pending registration activation boundary violated."
        )


    if (
        user.signup_method
        !=
        registration.provider
    ):
        raise RegistrationTransitionError(
            "Registration identity boundary violated."
        )


    identity_exists = (
        ExternalIdentity.objects
        .filter(
            user=user,
            provider=(
                registration.provider
            ),
        )
        .exists()
    )


    if not identity_exists:
        raise RegistrationTransitionError(
            "Verified identity binding required."
        )


    owner_membership_exists = (
        OrganizationUser.objects
        .filter(
            user=user,
            organization=organization,
            role="owner",
        )
        .exists()
    )


    if not owner_membership_exists:
        raise RegistrationTransitionError(
            "Pending owner membership required."
        )


@transaction.atomic
def approve_registration_request(
    *,
    registration_public_id,
    reviewer,
):
    _require_platform_reviewer(
        reviewer
    )

    registration = (
        _locked_registration(
            registration_public_id
        )
    )


    _assert_pending_integrity(
        registration
    )


    now = timezone.now()

    user = registration.user
    organization = (
        registration.organization
    )


    user.is_active = True

    user.save(
        update_fields=[
            "is_active",
        ]
    )


    organization.is_active = True

    organization.save(
        update_fields=[
            "is_active",
        ]
    )


    registration.status = (
        REGISTRATION_STATUS_APPROVED
    )

    registration.reviewed_at = now

    registration.reviewed_by = reviewer

    registration.rejection_reason = ""

    registration.save(
        update_fields=[
            "status",
            "reviewed_at",
            "reviewed_by",
            "rejection_reason",
        ]
    )


    _audit_registration(
        registration=registration,
        action=(
            "REGISTRATION_APPROVED"
        ),
        actor=reviewer,
    )


    return registration


@transaction.atomic
def reject_registration_request(
    *,
    registration_public_id,
    reviewer,
    rejection_reason="",
):
    _require_platform_reviewer(
        reviewer
    )

    registration = (
        _locked_registration(
            registration_public_id
        )
    )


    _assert_pending_integrity(
        registration
    )


    reason = str(
        rejection_reason
        or ""
    ).strip()


    now = timezone.now()

    registration.status = (
        REGISTRATION_STATUS_REJECTED
    )

    registration.reviewed_at = now

    registration.reviewed_by = reviewer

    registration.rejection_reason = reason

    registration.save(
        update_fields=[
            "status",
            "reviewed_at",
            "reviewed_by",
            "rejection_reason",
        ]
    )


    # Deliberately preserve:
    # - inactive user
    # - inactive workspace
    # - ExternalIdentity binding
    #
    # This prevents rejected identities from repeatedly
    # presenting as unrelated new applicants.

    _audit_registration(
        registration=registration,
        action=(
            "REGISTRATION_REJECTED"
        ),
        actor=reviewer,
    )


    return registration


def registration_review_state_for_verified_identity(
    *,
    provider,
    issuer,
    subject,
):
    """
    Resolve pending/rejected registration state only from the
    exact provider + issuer + subject identity binding.

    Email-only lookup is deliberately prohibited.
    """

    provider = str(
        provider
        or ""
    ).strip().lower()

    issuer = str(
        issuer
        or ""
    ).strip()

    subject = str(
        subject
        or ""
    ).strip()


    if (
        provider
        not in
        SUPPORTED_REGISTRATION_PROVIDERS
        or
        not issuer
        or
        not subject
    ):
        return None


    binding = (
        ExternalIdentity.objects
        .select_related(
            "user"
        )
        .filter(
            provider=provider,
            issuer=issuer,
            subject=subject,
        )
        .first()
    )


    if binding is None:
        return None


    user = binding.user


    if (
        user.signup_method
        != provider
    ):
        return None


    registration = (
        RegistrationRequest.objects
        .filter(
            user=user,
            provider=provider,
            status__in=[
                REGISTRATION_STATUS_PENDING,
                REGISTRATION_STATUS_REJECTED,
            ],
        )
        .first()
    )


    if registration is None:
        return None


    return {
        "status":
            registration.status,

        "registration_id":
            registration.public_id,
    }
