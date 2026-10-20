from django.db import migrations, models
from django.db.models import Case, F, Value, When


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0014_alter_property_assigned_agents'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='location',
            name='location_unique_root_slug',
        ),
        migrations.RemoveConstraint(
            model_name='propertyimage',
            name='property_image_one_primary_per_property',
        ),
        migrations.AddField(
            model_name='location',
            name='root_slug_key',
            field=models.GeneratedField(
                db_persist=True,
                expression=Case(
                    When(parent__isnull=True, then=F('slug')),
                    default=Value(None),
                ),
                output_field=models.CharField(max_length=140),
            ),
        ),
        migrations.AddField(
            model_name='propertyimage',
            name='primary_property_key',
            field=models.GeneratedField(
                db_persist=True,
                expression=Case(
                    When(is_primary=True, then=F('property_id')),
                    default=Value(None),
                ),
                output_field=models.BigIntegerField(),
            ),
        ),
        migrations.AddConstraint(
            model_name='location',
            constraint=models.UniqueConstraint(
                fields=('root_slug_key',),
                name='location_root_slug_unique',
            ),
        ),
        migrations.AddConstraint(
            model_name='propertyimage',
            constraint=models.UniqueConstraint(
                fields=('primary_property_key',),
                name='property_image_primary_slot_unique',
            ),
        ),
    ]
