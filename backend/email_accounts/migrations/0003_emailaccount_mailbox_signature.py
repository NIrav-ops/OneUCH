from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "email_accounts",
            "0002_emailaccount_history_sync_completed_at",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="emailaccount",
            name="signature_enabled",
            field=models.BooleanField(
                default=False,
            ),
        ),
        migrations.AddField(
            model_name="emailaccount",
            name="signature_text",
            field=models.TextField(
                blank=True,
                default="",
            ),
        ),
    ]
