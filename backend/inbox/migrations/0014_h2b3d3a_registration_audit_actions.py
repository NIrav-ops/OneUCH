from django.db import (
    migrations,
    models,
)


class Migration(
    migrations.Migration,
):

    dependencies = [
        (
            "inbox",
            "0013_authsec_rc1a_audit_actions",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="auditlog",
            name="action",
            field=models.CharField(
                choices=[
                    (
                        "ATTACHMENT_DOWNLOAD",
                        "Attachment Download",
                    ),
                    (
                        "ATTACHMENT_POLICY_UPDATE",
                        "Attachment Policy Update",
                    ),
                    (
                        "LOGIN",
                        "User Login",
                    ),
                    (
                        "LOGOUT",
                        "User Logout",
                    ),
                    (
                        "SIGNUP",
                        "User Signup",
                    ),
                    (
                        "SIGNUP_REGISTRY_VIEW",
                        "Signup Registry View",
                    ),
                    (
                        "REGISTRATION_REQUESTED",
                        "Registration Requested",
                    ),
                    (
                        "REGISTRATION_APPROVED",
                        "Registration Approved",
                    ),
                    (
                        "REGISTRATION_REJECTED",
                        "Registration Rejected",
                    ),
                ],
                db_index=True,
                max_length=50,
            ),
        ),
    ]
