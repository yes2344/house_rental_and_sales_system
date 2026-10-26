from django.db import migrations, models


def correct_branding(apps, schema_editor):
    database = schema_editor.connection.alias
    BrokerageSettings = apps.get_model('portal_admin', 'BrokerageSettings')
    HomepageNote = apps.get_model('portal_admin', 'HomepageNote')
    PublicInformationPage = apps.get_model('portal_admin', 'PublicInformationPage')

    for settings in BrokerageSettings.objects.using(database).all().iterator():
        updates = {}
        for field in ('site_name', 'business_name', 'footer_copyright'):
            value = getattr(settings, field)
            if value and value.strip().casefold() in {'habasha property center', 'habeshahome'}:
                updates[field] = 'Habesha Property Center'
            elif value and 'Habasha' in value:
                updates[field] = value.replace('Habasha', 'Habesha')
        if updates:
            BrokerageSettings.objects.using(database).filter(pk=settings.pk).update(**updates)

    for note in HomepageNote.objects.using(database).all().iterator():
        updates = {
            field: getattr(note, field).replace('Habasha', 'Habesha')
            for field in ('title', 'text')
            if 'Habasha' in getattr(note, field)
        }
        if updates:
            HomepageNote.objects.using(database).filter(pk=note.pk).update(**updates)

    for page in PublicInformationPage.objects.using(database).all().iterator():
        updates = {
            field: getattr(page, field).replace('Habasha', 'Habesha')
            for field in (
                'title_en',
                'title_am',
                'introduction_en',
                'introduction_am',
                'body_en',
                'body_am',
            )
            if 'Habasha' in getattr(page, field)
        }
        if updates:
            PublicInformationPage.objects.using(database).filter(pk=page.pk).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        ('portal_admin', '0011_homepagenote_image'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='brokeragesettings',
            options={'verbose_name_plural': 'Habesha Property Center contact settings'},
        ),
        migrations.AlterField(
            model_name='brokeragesettings',
            name='site_name',
            field=models.CharField(default='Habesha Property Center', max_length=100),
        ),
        migrations.RunPython(correct_branding, migrations.RunPython.noop),
    ]
