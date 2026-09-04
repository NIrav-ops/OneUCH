import uuid

import inbox.models
from django.db import migrations, models


def backfill_workspace_public_ids(
    apps,
    schema_editor,
):

    Organization = apps.get_model(
        "inbox",
        "Organization",
    )

    for organization in (
        Organization.objects.filter(
            public_id__isnull=True
        )
    ):

        while True:

            value = (
                "WSP-"
                + uuid.uuid4().hex[
                    :12
                ].upper()
            )

            exists = (
                Organization.objects
                .filter(
                    public_id=value
                )
                .exists()
            )

            if not exists:
                break

        organization.public_id = (
            value
        )

        organization.save(
            update_fields=[
                "public_id",
            ]
        )


class Migration(
    migrations.Migration
):

    dependencies = [
        (
            "inbox",
            "0011_recipient_directory",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="public_id",
            field=models.CharField(
                blank=True,
                editable=False,
                max_length=20,
                null=True,
                unique=True,
            ),
        ),
        migrations.RunPython(
            backfill_workspace_public_ids,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="organization",
            name="public_id",
            field=models.CharField(
                default=(
                    inbox.models
                    .generate_workspace_public_id
                ),
                editable=False,
                max_length=20,
                unique=True,
            ),
        ),
    ]
