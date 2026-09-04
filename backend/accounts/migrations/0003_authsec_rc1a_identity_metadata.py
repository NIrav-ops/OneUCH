import uuid

import accounts.models
from django.db import migrations, models
from django.db.models.functions import Lower


def backfill_user_public_ids(
    apps,
    schema_editor,
):

    User = apps.get_model(
        "accounts",
        "User",
    )

    for user in User.objects.filter(
        public_id__isnull=True
    ):

        while True:

            value = (
                "USR-"
                + uuid.uuid4().hex[
                    :12
                ].upper()
            )

            if not User.objects.filter(
                public_id=value
            ).exists():
                break

        user.public_id = value

        user.save(
            update_fields=[
                "public_id",
            ]
        )


class Migration(
    migrations.Migration
):

    dependencies = [
        (
            "accounts",
            "0002_alter_user_is_superuser",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="public_id",
            field=models.CharField(
                blank=True,
                editable=False,
                max_length=20,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="signup_method",
            field=models.CharField(
                choices=[
                    (
                        "legacy",
                        "Legacy",
                    ),
                    (
                        "work_email",
                        "Work email",
                    ),
                    (
                        "google",
                        "Google",
                    ),
                    (
                        "microsoft",
                        "Microsoft",
                    ),
                ],
                default="legacy",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="last_auth_method",
            field=models.CharField(
                blank=True,
                choices=[
                    (
                        "legacy",
                        "Legacy",
                    ),
                    (
                        "work_email",
                        "Work email",
                    ),
                    (
                        "google",
                        "Google",
                    ),
                    (
                        "microsoft",
                        "Microsoft",
                    ),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.RunPython(
            backfill_user_public_ids,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="user",
            name="public_id",
            field=models.CharField(
                default=(
                    accounts.models
                    .generate_user_public_id
                ),
                editable=False,
                max_length=20,
                unique=True,
            ),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_ci_unique",
            ),
        ),
    ]
