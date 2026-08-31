from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "inbox",
            "0009_inboxmessage_expected_response_analyzed",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="inboxmessage",
            name="recipient_meta",
            field=models.JSONField(
                blank=True,
                default=dict,
            ),
        ),
        migrations.AddField(
            model_name="inboxmessage",
            name="sender_meta",
            field=models.JSONField(
                blank=True,
                default=dict,
            ),
        ),
    ]
