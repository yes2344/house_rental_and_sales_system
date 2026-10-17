import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('owner_announcements', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='ownerannouncement',
            name='assigned_reviewer',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assigned_owner_announcements',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddIndex(
            model_name='ownerannouncement',
            index=models.Index(
                fields=['assigned_reviewer', 'status'],
                name='owner_announce_reviewer_idx',
            ),
        ),
        migrations.AlterField(
            model_name='ownerannouncementevent',
            name='event_type',
            field=models.CharField(
                choices=[
                    ('submitted', 'Submitted'),
                    ('assigned', 'Assigned for review'),
                    ('unassigned', 'Review assignment removed'),
                    ('corrections_requested', 'Corrections requested'),
                    ('approved', 'Approved'),
                    ('rejected', 'Rejected'),
                    ('edited', 'Owner edited'),
                    ('renewal_requested', 'Renewal requested'),
                    ('suspended', 'Suspended'),
                    ('withdrawn', 'Withdrawn'),
                    ('expired', 'Expired'),
                ],
                max_length=32,
            ),
        ),
    ]
