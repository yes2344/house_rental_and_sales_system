from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def rename_managed_service_type(apps, schema_editor):
    Property = apps.get_model('properties', 'Property')
    Property.objects.using(schema_editor.connection.alias).filter(
        service_type='broker_managed',
    ).update(service_type='agent_managed')


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0012_secure_property_images_and_reviewer_assignment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='propertybrokerassignment',
            name='broker_assignment_user_idx',
        ),
        migrations.RemoveConstraint(
            model_name='propertybrokerassignment',
            name='property_broker_assignment_unique',
        ),
        migrations.RenameModel(
            old_name='PropertyBrokerAssignment',
            new_name='PropertyAgentAssignment',
        ),
        migrations.RenameField(
            model_name='propertyagentassignment',
            old_name='broker',
            new_name='agent',
        ),
        migrations.RenameField(
            model_name='property',
            old_name='assigned_brokers',
            new_name='assigned_agents',
        ),
        migrations.RunPython(rename_managed_service_type, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='property',
            name='service_type',
            field=models.CharField(
                choices=[('agent_managed', 'Agent-managed'), ('owner_announced', 'Owner-announced')],
                default='agent_managed',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='propertyagentassignment',
            name='agent',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='property_agent_assignments',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='propertyagentassignment',
            name='granted_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='granted_property_agent_assignments',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='propertyagentassignment',
            name='property',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='agent_assignments',
                to='properties.property',
            ),
        ),
        migrations.AddIndex(
            model_name='propertyagentassignment',
            index=models.Index(fields=['agent', 'granted_at'], name='agent_assignment_user_idx'),
        ),
        migrations.AddConstraint(
            model_name='propertyagentassignment',
            constraint=models.UniqueConstraint(
                fields=('property', 'agent'),
                name='property_agent_assignment_unique',
            ),
        ),
    ]
