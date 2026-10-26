# Move Django's model state to domain apps while preserving the existing tables.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('properties', '0001_preserve_legacy_tables'),
        ('user', '0003_property_listing_type'),
        ('viewings', '0001_preserve_legacy_table'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='viewingrequest',
                    name='property',
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='viewing_requests',
                        to='properties.property',
                    ),
                ),
                migrations.DeleteModel(name='ViewingRequest'),
                migrations.DeleteModel(name='PropertyImage'),
                migrations.DeleteModel(name='Property'),
            ],
        ),
    ]
