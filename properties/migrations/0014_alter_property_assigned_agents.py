from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0013_standardize_agent_terms'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='property',
            name='assigned_agents',
            field=models.ManyToManyField(
                blank=True,
                related_name='assigned_properties',
                through='properties.PropertyAgentAssignment',
                through_fields=('property', 'agent'),
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
