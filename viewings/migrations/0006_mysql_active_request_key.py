from django.db import migrations, models
from django.db.models import Case, F, Value, When


class Migration(migrations.Migration):

    dependencies = [
        ('viewings', '0005_viewingrequest_requester_deleted_at'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='viewingrequest',
            name='viewing_one_active_request_per_user_property',
        ),
        migrations.AddField(
            model_name='viewingrequest',
            name='active_requester_key',
            field=models.GeneratedField(
                db_persist=True,
                expression=Case(
                    When(
                        requester__isnull=False,
                        status__in=['pending', 'proposed', 'confirmed', 'declined'],
                        then=F('requester_id'),
                    ),
                    default=Value(None),
                ),
                output_field=models.BigIntegerField(),
            ),
        ),
        migrations.AddConstraint(
            model_name='viewingrequest',
            constraint=models.UniqueConstraint(
                fields=('active_requester_key', 'property'),
                name='viewing_active_request_property_unique',
            ),
        ),
    ]
