from django.db import migrations, models


class Migration(
    migrations.Migration
):

    dependencies = [
        (
            "inbox",
            "0012_authsec_rc1a_workspace_identity",
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
                ],
                db_index=True,
                max_length=50,
            ),
        ),
    ]
