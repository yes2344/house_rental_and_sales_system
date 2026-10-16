from django.db import migrations, models


def create_public_information_pages(apps, schema_editor):
    PublicInformationPage = apps.get_model('portal_admin', 'PublicInformationPage')
    PublicInformationPage.objects.using(schema_editor.connection.alias).bulk_create([
        PublicInformationPage(
            page='about',
            title_en='About Habasha Property Center',
            title_am='ስለ Habasha Property Center',
            introduction_en='Habasha Property Center brings property listings for rent and sale into one place.',
            introduction_am='Habasha Property Center ለኪራይና ለሽያጭ የቀረቡ የንብረት ዝርዝሮችን በአንድ ቦታ ያቀርባል።',
            body_en='Browse listing details, request a viewing, or contact the configured service channels.',
            body_am='ዝርዝሮችን ይመልከቱ፣ የጉብኝት ጥያቄ ያቅርቡ ወይም የተዋቀሩትን የግንኙነት መንገዶች ይጠቀሙ።',
        ),
        PublicInformationPage(
            page='contact',
            title_en='Contact',
            title_am='ያግኙን',
            introduction_en='Reach Habasha Property Center using the contact options configured below.',
            introduction_am='ከታች በተዋቀሩት የግንኙነት መንገዶች Habasha Property Centerን ያግኙ።',
        ),
        PublicInformationPage(
            page='property-management',
            title_en='Property management',
            title_am='የንብረት አስተዳደር',
            introduction_en='We help property owners present their listings and connect with people looking to rent or buy.',
            introduction_am='የንብረት ባለቤቶች ዝርዝሮቻቸውን ለማቅረብና ለመከራየት ወይም ለመግዛት ከሚፈልጉ ሰዎች ጋር ለመገናኘት እናግዛለን።',
            body_en='Submit property details and photos for review. An authorized agent reviews eligible submissions before publication. Contact us to discuss property-management services.',
            body_am='የንብረት መረጃና ፎቶዎችን ለግምገማ ያስገቡ። ለህትመት ብቁ የሆኑ ማስገቢያዎችን የተፈቀደ ኤጀንት ይገመግማል። ስለ ንብረት አስተዳደር አገልግሎቶች ለመወያየት ያግኙን።',
        ),
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('portal_admin', '0008_alter_socialmedialink_platform'),
    ]

    operations = [
        migrations.CreateModel(
            name='PublicInformationPage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page', models.CharField(choices=[('about', 'About'), ('contact', 'Contact'), ('property-management', 'Property management')], max_length=32, unique=True)),
                ('title_en', models.CharField(max_length=160)),
                ('title_am', models.CharField(max_length=160)),
                ('introduction_en', models.CharField(max_length=500)),
                ('introduction_am', models.CharField(max_length=500)),
                ('body_en', models.TextField(blank=True, max_length=5000)),
                ('body_am', models.TextField(blank=True, max_length=5000)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['page'],
            },
        ),
        migrations.RunPython(create_public_information_pages, migrations.RunPython.noop),
    ]
