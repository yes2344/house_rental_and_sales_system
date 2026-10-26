from django.db import migrations


COMMON_AMENITIES = (
    ('Balcony', 'balcony'),
    ('Elevator', 'elevator'),
    ('Electricity', 'electricity'),
    ('Furnished', 'furnished'),
    ('Garden', 'garden'),
    ('Internet', 'internet'),
    ('Kitchen', 'kitchen'),
    ('Living room', 'living-room'),
    ('Parking', 'parking'),
    ('Security', 'security'),
    ('Unfurnished', 'unfurnished'),
    ('Water', 'water'),
)


def seed_common_amenities(apps, schema_editor):
    Amenity = apps.get_model('properties', 'Amenity')
    database = schema_editor.connection.alias

    for name, slug in COMMON_AMENITIES:
        if not Amenity.objects.using(database).filter(name=name).exists():
            Amenity.objects.using(database).get_or_create(
                slug=slug,
                defaults={'name': name},
            )


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0009_location_aliases_am_location_aliases_en'),
    ]

    operations = [
        migrations.RunPython(seed_common_amenities, migrations.RunPython.noop),
    ]