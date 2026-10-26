# Preserve the table created by user.0001 without recreating or copying data.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('properties', '0001_preserve_legacy_tables'),
        ('user', '0003_property_listing_type'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='ViewingRequest',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('full_name', models.CharField(max_length=200)),
                        ('email', models.EmailField(max_length=254)),
                        ('phone', models.CharField(max_length=50)),
                        ('preferred_date', models.DateField()),
                        ('message', models.TextField(blank=True)),
                        ('status', models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('agent_notes', models.TextField(blank=True)),
                        ('preferred_time', models.TimeField(blank=True, null=True)),
                        ('scheduled_date', models.DateField(blank=True, null=True)),
                        ('scheduled_time', models.TimeField(blank=True, null=True)),
                        ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='viewing_requests', to='properties.property')),
                    ],
                    options={
                        'db_table': 'user_viewingrequest',
                    },
                ),
            ],
        ),
    ]
