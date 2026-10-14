from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viewings', '0004_viewingrequestevent_message_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='viewingrequest',
            name='requester_deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
