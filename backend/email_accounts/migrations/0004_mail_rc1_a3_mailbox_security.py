
import base64
import hashlib

import django.db.models.deletion

from cryptography.fernet import (
    Fernet,
)

from django.conf import (
    settings,
)

from django.db import (
    migrations,
    models,
)


def _fernet():
    material = (
        "oneuch-mail-credential-v1:"
        + str(
            settings.SECRET_KEY
        )
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


def forwards(
    apps,
    schema_editor,
):
    EmailAccount = apps.get_model(
        "email_accounts",
        "EmailAccount",
    )

    OrganizationUser = apps.get_model(
        "inbox",
        "OrganizationUser",
    )

    cipher = None

    for account in (
        EmailAccount.objects
        .all()
        .iterator()
    ):
        organization_id = (
            OrganizationUser.objects
            .filter(
                user_id=account.user_id
            )
            .values_list(
                "organization_id",
                flat=True,
            )
            .first()
        )

        if organization_id is None:
            raise RuntimeError(
                "MAIL-RC1/A3 found an EmailAccount "
                "without workspace membership."
            )

        account.organization_id = (
            organization_id
        )

        plaintext = (
            account.smtp_password
            or ""
        )

        if plaintext:
            if cipher is None:
                cipher = _fernet()

            account.credential_ciphertext = (
                cipher.encrypt(
                    str(
                        plaintext
                    ).encode(
                        "utf-8"
                    )
                )
                .decode(
                    "ascii"
                )
            )

        account.save(
            update_fields=[
                "organization",
                "credential_ciphertext",
            ]
        )


def backwards(
    apps,
    schema_editor,
):
    EmailAccount = apps.get_model(
        "email_accounts",
        "EmailAccount",
    )

    cipher = None

    for account in (
        EmailAccount.objects
        .exclude(
            credential_ciphertext__isnull=True
        )
        .exclude(
            credential_ciphertext=""
        )
        .iterator()
    ):
        if cipher is None:
            cipher = _fernet()

        account.smtp_password = (
            cipher.decrypt(
                account
                .credential_ciphertext
                .encode(
                    "ascii"
                )
            )
            .decode(
                "utf-8"
            )
        )

        account.save(
            update_fields=[
                "smtp_password",
            ]
        )


class Migration(
    migrations.Migration
):

    dependencies = [
        (
            "email_accounts",
            "0003_emailaccount_mailbox_signature",
        ),
        (
            "inbox",
            "0013_authsec_rc1a_audit_actions",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="emailaccount",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=(
                    django.db.models
                    .deletion.CASCADE
                ),
                related_name="email_accounts",
                to="inbox.organization",
            ),
        ),

        migrations.AddField(
            model_name="emailaccount",
            name="credential_ciphertext",
            field=models.TextField(
                blank=True,
                editable=False,
                help_text=(
                    "Encrypted generic mailbox credential."
                ),
                null=True,
            ),
        ),

        migrations.RunPython(
            forwards,
            backwards,
        ),

        migrations.AlterField(
            model_name="emailaccount",
            name="organization",
            field=models.ForeignKey(
                on_delete=(
                    django.db.models
                    .deletion.CASCADE
                ),
                related_name="email_accounts",
                to="inbox.organization",
            ),
        ),

        migrations.AddConstraint(
            model_name="emailaccount",
            constraint=models.UniqueConstraint(
                fields=(
                    "organization",
                    "account_type",
                    "email_address",
                ),
                name=(
                    "uniq_mailbox_org_type_email"
                ),
            ),
        ),

        migrations.RemoveField(
            model_name="emailaccount",
            name="smtp_password",
        ),

        migrations.AlterField(
            model_name="emailaccount",
            name="account_type",
            field=models.CharField(
                choices=[
                    (
                        "imap",
                        "IMAP / SMTP",
                    ),
                    (
                        "gmail",
                        "Gmail (OAuth)",
                    ),
                    (
                        "outlook",
                        "Outlook / Microsoft 365",
                    ),
                ],
                max_length=20,
            ),
        ),
    ]
