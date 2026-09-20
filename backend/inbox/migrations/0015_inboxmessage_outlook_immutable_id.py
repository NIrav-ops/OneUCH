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
            "0014_h2b3d3a_registration_audit_actions",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="inboxmessage",
            name="outlook_immutable_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text=(
                    "Stable Microsoft Graph message identity "
                    "for Outlook folder moves"
                ),
                max_length=255,
                null=True,
            ),
        ),
    ]
