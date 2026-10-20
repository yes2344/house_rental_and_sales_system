from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viewings', '0006_mysql_active_request_key'),
    ]

    operations = [
        migrations.AlterField(
            model_name='viewingrequestevent',
            name='event_type',
            field=models.CharField(
                choices=[
                    ('submitted', 'Submitted'),
                    ('proposal_sent', 'Appointment proposed'),
                    ('proposal_revised', 'Appointment proposal revised'),
                    ('request_updated', 'Viewing request updated'),
                    ('proposal_accepted', 'Appointment proposal accepted'),
                    ('proposal_declined', 'Appointment proposal declined'),
                    ('rejected', 'Request declined by property manager'),
                    ('request_confirmed', 'Requested appointment confirmed'),
                    ('cancelled', 'Appointment or request cancelled'),
                    ('completed', 'Viewing completed'),
                ],
                max_length=32,
            ),
        ),
    ]
