import re

from django.db import migrations, models


SITE_NAME = 'habeshapropertycenter'
LEGACY_NAMES = re.compile(
    r'\b(?:Habasha Property Center|Habesha Property Center|Habesha Home Center|'
    r'kekalehabesha home|habeshahome)\b',
    re.IGNORECASE,
)


def standardize_site_name(apps, schema_editor):
    database = schema_editor.connection.alias
    BrokerageSettings = apps.get_model('portal_admin', 'BrokerageSettings')
    HomepageNote = apps.get_model('portal_admin', 'HomepageNote')
    PublicInformationPage = apps.get_model('portal_admin', 'PublicInformationPage')

    for settings in BrokerageSettings.objects.using(database).all().iterator():
        updates = {}
        for field in ('site_name', 'business_name', 'footer_copyright'):
            value = getattr(settings, field)
            standardized = LEGACY_NAMES.sub(SITE_NAME, value) if value else value
            if standardized != value:
                updates[field] = standardized
        if updates:
            BrokerageSettings.objects.using(database).filter(pk=settings.pk).update(**updates)

    for model, fields in (
        (HomepageNote, ('title', 'text')),
        (PublicInformationPage, (
            'title_en',
            'title_am',
            'introduction_en',
            'introduction_am',
            'body_en',
            'body_am',
        )),
    ):
        for item in model.objects.using(database).all().iterator():
            updates = {}
            for field in fields:
                value = getattr(item, field)
                standardized = LEGACY_NAMES.sub(SITE_NAME, value) if value else value
                if standardized != value:
                    updates[field] = standardized
            if updates:
                model.objects.using(database).filter(pk=item.pk).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        ('portal_admin', '0012_correct_habesha_branding'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='brokeragesettings',
            options={'verbose_name_plural': 'habeshapropertycenter contact settings'},
        ),
        migrations.AlterField(
            model_name='brokeragesettings',
            name='site_name',
            field=models.CharField(default='habeshapropertycenter', max_length=100),
        ),
        migrations.RunPython(standardize_site_name, migrations.RunPython.noop),
    ]
