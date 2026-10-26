import re

from django.db import migrations, models


SITE_NAME = 'Infinity House'
LEGACY_BRAND_NAMES = re.compile(
    r'\b(?:habeshapropertycenter|habasha\s+property\s+center|'
    r'habesha\s+property\s+center|habesha\s+home\s+center|'
    r'kekalehabesha\s+home|habeshahome)\b',
    re.IGNORECASE,
)


def rename_brand(apps, schema_editor):
    database = schema_editor.connection.alias
    BrokerageSettings = apps.get_model('portal_admin', 'BrokerageSettings')
    HomepageNote = apps.get_model('portal_admin', 'HomepageNote')
    PublicInformationPage = apps.get_model('portal_admin', 'PublicInformationPage')

    for settings in BrokerageSettings.objects.using(database).all().iterator():
        updates = {}
        for field in ('site_name', 'business_name', 'footer_copyright'):
            value = getattr(settings, field)
            renamed = LEGACY_BRAND_NAMES.sub(SITE_NAME, value) if value else value
            if renamed != value:
                updates[field] = renamed
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
                renamed = LEGACY_BRAND_NAMES.sub(SITE_NAME, value) if value else value
                if renamed != value:
                    updates[field] = renamed
            if updates:
                model.objects.using(database).filter(pk=item.pk).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        ('portal_admin', '0013_standardize_site_name'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='brokeragesettings',
            options={'verbose_name_plural': 'Infinity House contact settings'},
        ),
        migrations.AlterField(
            model_name='brokeragesettings',
            name='site_name',
            field=models.CharField(default='Infinity House', max_length=100),
        ),
        migrations.RunPython(rename_brand, migrations.RunPython.noop),
    ]
