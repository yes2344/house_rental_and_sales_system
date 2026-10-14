from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image, ImageDraw, ImageFont

from properties.models import Amenity, Location, Property, PropertyImage


SAMPLE_MARKER = '[SAMPLE LISTING - NOT REAL]'
IMAGE_CAPTIONS = tuple(
    f'Sample illustration {index} - not a property photograph.'
    for index in range(1, 6)
)

CITIES = (
    {
        'name': 'Addis Ababa',
        'slug': 'addis-ababa',
        'location_type': Location.Type.CITY_ADMINISTRATION,
        'aliases_en': ['Addis'],
        'palette': ((232, 239, 229), (37, 82, 63), (200, 151, 83)),
        'price_factor': 1.0,
    },
    {
        'name': 'Bahir Dar',
        'slug': 'bahir-dar',
        'location_type': Location.Type.CITY,
        'aliases_en': ['bahidar'],
        'palette': ((225, 239, 242), (37, 91, 112), (214, 156, 74)),
        'price_factor': 0.72,
    },
    {
        'name': 'Hawassa',
        'slug': 'hawassa',
        'location_type': Location.Type.CITY,
        'aliases_en': ['Awassa'],
        'palette': ((239, 234, 219), (76, 93, 54), (193, 123, 72)),
        'price_factor': 0.68,
    },
)

PROPERTY_TYPES = (
    ('house', 'House', 0.26),
    ('apartment', 'Apartment', 0.24),
    ('condominium', 'Condominium', 0.16),
    ('villa', 'Villa', 0.12),
    ('land', 'Land', 0.08),
    ('office', 'Office', 0.06),
    ('shop', 'Shop', 0.04),
    ('warehouse', 'Warehouse', 0.04),
)

AMENITY_SLUGS = (
    'balcony',
    'electricity',
    'garden',
    'internet',
    'parking',
    'security',
    'water',
)


def render_demo_image(city, property_title, image_number):
    background, building, accent = city['palette']
    image = Image.new('RGB', (960, 640), background)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    variation = image_number % 3
    ground_y = 475 + variation * 12
    draw.rectangle((0, ground_y, 960, 640), fill=(222, 215, 195))
    draw.ellipse((730, 70, 860, 200), fill=(244, 205, 123))

    building_left = 205 + image_number * 18
    building_right = 720 - image_number * 12
    building_top = 190 + variation * 25
    draw.rectangle(
        (building_left, building_top, building_right, ground_y),
        fill=building,
    )
    draw.polygon(
        [
            (building_left - 34, building_top + 8),
            ((building_left + building_right) // 2, building_top - 94),
            (building_right + 34, building_top + 8),
        ],
        fill=accent,
    )

    for row in range(2):
        for column in range(3):
            x = building_left + 45 + column * 105
            y = building_top + 55 + row * 95
            draw.rectangle((x, y, x + 52, y + 57), fill=(242, 236, 215))
            draw.line((x + 26, y, x + 26, y + 57), fill=building, width=3)

    draw.rectangle(
        (0, 520, 960, 640),
        fill=(255, 255, 255),
    )
    draw.text((32, 538), 'DEMO IMAGE - NOT A PROPERTY PHOTO', fill=(140, 44, 36), font=font)
    draw.text((32, 565), f"{city['name']} | {property_title}", fill=(36, 48, 40), font=font)
    draw.text((32, 590), f'Sample illustration {image_number + 1} of 5', fill=(74, 82, 74), font=font)

    buffer = BytesIO()
    image.save(buffer, format='JPEG', quality=82, optimize=True)
    return buffer.getvalue()


class Command(BaseCommand):
    help = (
        'Create up to 60 clearly marked sample listings in Addis Ababa, Bahir Dar, '
        'and Hawassa, with generated demo illustration images.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=60,
            help='Number of sample listings to create (maximum 60; default: 60).',
        )
        parser.add_argument(
            '--images-per-property',
            type=int,
            default=5,
            help='Number of generated sample illustrations per listing (maximum 5).',
        )

    def handle(self, *args, **options):
        count = options['count']
        images_per_property = options['images_per_property']
        if not 1 <= count <= 60:
            raise CommandError('--count must be between 1 and 60.')
        if not 1 <= images_per_property <= 5:
            raise CommandError('--images-per-property must be between 1 and 5.')

        if not Amenity.objects.filter(slug__in=AMENITY_SLUGS).exists():
            raise CommandError(
                'Common amenities are missing. Apply the properties migrations first.'
            )
        missing_amenities = set(AMENITY_SLUGS) - set(
            Amenity.objects.filter(slug__in=AMENITY_SLUGS).values_list('slug', flat=True)
        )
        if missing_amenities:
            raise CommandError(
                'Missing common amenities: ' + ', '.join(sorted(missing_amenities))
            )

        with transaction.atomic():
            country, _ = Location.objects.get_or_create(
                parent=None,
                slug='ethiopia',
                defaults={
                    'name': 'Ethiopia',
                    'location_type': Location.Type.COUNTRY,
                    'is_active': True,
                },
            )
            city_locations = {}
            for city in CITIES:
                location, _ = Location.objects.get_or_create(
                    parent=country,
                    slug=city['slug'],
                    defaults={
                        'name': city['name'],
                        'aliases_en': city['aliases_en'],
                        'location_type': city['location_type'],
                        'is_active': True,
                    },
                )
                city_locations[city['slug']] = location

            amenities = list(Amenity.objects.filter(slug__in=AMENITY_SLUGS))
            created_count = 0
            updated_count = 0
            image_count = 0

            for index in range(count):
                city = CITIES[index % len(CITIES)]
                city_index = index // len(CITIES) + 1
                type_slug, type_label, type_factor = PROPERTY_TYPES[index % len(PROPERTY_TYPES)]
                listing_type = (
                    Property.ListingType.RENT if index % 3 == 0 else Property.ListingType.SALE
                )
                title = f'{SAMPLE_MARKER} {city["name"]} {type_label} {city_index:02d}'
                slug = f'demo-{city["slug"]}-{type_slug}-{city_index:02d}'
                existing = Property.objects.filter(slug=slug).first()
                if existing and not existing.title.startswith(SAMPLE_MARKER):
                    raise CommandError(
                        f'Cannot reuse slug {slug!r}; an existing non-sample listing owns it.'
                    )

                bedrooms = 0 if type_slug in ('land', 'office', 'shop', 'warehouse') else 1 + index % 5
                bathrooms = 0 if type_slug == 'land' else 1 + index % 3
                area_sqm = Decimal(45 + (index * 19) % 260)
                price_base = (
                    18000 + (index * 2700) % 72000
                    if listing_type == Property.ListingType.RENT
                    else 1_200_000 + (index * 185_000) % 8_000_000
                )
                price = Decimal(price_base * city['price_factor'] * type_factor).quantize(Decimal('1'))
                description = (
                    f'{SAMPLE_MARKER} Demonstration listing created for interface testing only. '
                    f'This fictional {type_label.lower()} example is assigned to {city["name"]} '
                    'at city level only. It has no verified street address, neighborhood, '
                    'owner, broker, availability, market price, or property photograph. '
                    'Do not use this sample as a real offer or contact a real person about it.'
                )
                defaults = {
                    'title': title,
                    'location': city['name'],
                    'administrative_location': city_locations[city['slug']],
                    'property_type': type_slug,
                    'listing_type': listing_type,
                    'price': price,
                    'rental_frequency': (
                        Property.RentalFrequency.MONTHLY
                        if listing_type == Property.ListingType.RENT
                        else ''
                    ),
                    'bedrooms': bedrooms,
                    'bathrooms': bathrooms,
                    'area_sqft': int(area_sqm * Decimal('10.7639')),
                    'area_value': area_sqm,
                    'area_unit': Property.AreaUnit.SQUARE_METRES,
                    'description': description,
                    'features': (
                        'Sample data only. Values are illustrative and are not verified '
                        'property specifications.'
                    ),
                    'status': Property.Status.AVAILABLE,
                    'publication_status': Property.PublicationStatus.PUBLISHED,
                    'service_type': Property.ServiceType.BROKER_MANAGED,
                    'is_featured': False,
                    'contact_name': '',
                    'contact_phone': '',
                    'contact_email': '',
                }
                property_obj, created = Property.objects.update_or_create(
                    slug=slug,
                    defaults=defaults,
                )
                property_obj.amenities.set(amenities[: 2 + index % (len(amenities) - 1)])
                if created:
                    created_count += 1
                else:
                    updated_count += 1

                for image_number, caption in enumerate(IMAGE_CAPTIONS[:images_per_property]):
                    if PropertyImage.objects.filter(property=property_obj, caption=caption).exists():
                        continue
                    image_bytes = render_demo_image(city, title, image_number)
                    filename = f'{slug}-sample-{image_number + 1}.jpg'
                    PropertyImage.objects.create(
                        property=property_obj,
                        image=ContentFile(image_bytes, name=filename),
                        caption=caption,
                        is_primary=image_number == 0,
                    )
                    image_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Sample data ready: {created_count} created, {updated_count} updated, '
            f'{image_count} generated illustrations added across {len(CITIES)} cities. '
            'All listings are visibly marked as samples and are published for local testing.'
        ))
