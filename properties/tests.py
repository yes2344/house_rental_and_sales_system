from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from PIL import Image

from accounts.models import Profile
from properties.models import Amenity, Property, PropertyBrokerAssignment, PropertyImage


class PropertyConstraintTests(TestCase):
    def make_property(self, **overrides):
        values = {
            'title': 'Constraint Test Property',
            'location': 'Submitted location',
            'property_type': 'house',
            'listing_type': Property.ListingType.SALE,
            'price': 100000,
            'description': 'A test listing.',
            'status': Property.Status.AVAILABLE,
        }
        values.update(overrides)
        return Property.objects.create(**values)

    def test_zero_price_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_property(price=0)

    def test_negative_price_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_property(price=-1)

    def test_sold_status_requires_sale_listing(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_property(
                    listing_type=Property.ListingType.RENT,
                    status=Property.Status.SOLD,
                )

    def test_rented_sale_listing_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_property(
                    listing_type=Property.ListingType.SALE,
                    status=Property.Status.RENTED,
                )

    def test_existing_active_status_remains_valid_for_legacy_data(self):
        property_obj = self.make_property(status=Property.Status.LEGACY_ACTIVE)
        self.assertEqual(property_obj.status, 'active')


class PublicPropertyApiTests(APITestCase):
    def setUp(self):
        self.property = Property.objects.create(
            title='Available family house',
            slug='available-family-house-api',
            location='Submitted location',
            property_type='house',
            listing_type=Property.ListingType.SALE,
            price=500000,
            bedrooms=3,
            bathrooms=2,
            area_sqft=1500,
            description='A family home with a garden.',
            features='Garden',
            status=Property.Status.AVAILABLE,
            publication_status=Property.PublicationStatus.PUBLISHED,
        )
        self.garden = Amenity.objects.create(name='Garden', slug='garden')
        self.property.amenities.add(self.garden)

    def test_public_list_returns_paginated_etb_properties(self):
        response = self.client.get(reverse('api:property-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        result = response.data['results'][0]
        self.assertEqual(result['currency'], 'ETB')
        self.assertEqual(result['category'], 'house')
        self.assertEqual(result['status'], 'available')
        self.assertNotIn('contact_phone', result)
        self.assertNotIn('owner', result)

    def test_public_amenity_list_returns_existing_localized_options(self):
        response = self.client.get(reverse('api:amenity-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0], {
            'id': self.garden.id,
            'name': 'Garden',
            'name_am': '',
            'slug': 'garden',
        })

    def test_combined_filters_and_amenities_are_applied(self):
        response = self.client.get(
            reverse('api:property-list'),
            {
                'listing_type': 'sale',
                'property_type': 'house',
                'min_price': '400000',
                'max_price': '600000',
                'min_bedrooms': '3',
                'min_size': '1000',
                'amenities': 'garden',
                'search': 'family',
                'ordering': 'price',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['slug'], self.property.slug)

    def test_invalid_filter_returns_consistent_validation_error(self):
        response = self.client.get(
            reverse('api:property-list'),
            {'min_price': 'not-a-price'},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error']['status_code'], 400)
        self.assertIn('min_price', response.data['error']['details'])

    def test_public_list_hides_unavailable_or_unpublished_properties(self):
        Property.objects.create(
            title='Sold listing',
            slug='sold-listing-api',
            location='Submitted location',
            price=100000,
            description='Not available.',
            status=Property.Status.SOLD,
            publication_status=Property.PublicationStatus.PUBLISHED,
        )
        Property.objects.create(
            title='Pending listing',
            slug='pending-listing-api',
            location='Submitted location',
            price=200000,
            description='Not published.',
            status=Property.Status.AVAILABLE,
            publication_status=Property.PublicationStatus.PENDING_REVIEW,
        )

        response = self.client.get(reverse('api:property-list'))

        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['slug'], self.property.slug)

    def test_detail_includes_public_contact_and_localized_amenity_fields(self):
        self.property.contact_phone = '+251900000000'
        self.property.contact_email = 'contact@example.com'
        self.property.save()

        response = self.client.get(
            reverse('api:property-detail', kwargs={'slug': self.property.slug})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['contact_phone'], '+251900000000')
        self.assertEqual(response.data['amenities'][0]['slug'], 'garden')
        self.assertEqual(response.data['currency'], 'ETB')

    def test_detail_does_not_expose_unavailable_property(self):
        self.property.status = Property.Status.RENTED
        self.property.listing_type = Property.ListingType.RENT
        self.property.save()

        response = self.client.get(
            reverse('api:property-detail', kwargs={'slug': self.property.slug})
        )

        self.assertEqual(response.status_code, 404)

    def test_pagination_can_be_changed_within_configured_limit(self):
        Property.objects.create(
            title='Second available house',
            slug='second-available-house-api',
            location='Submitted location',
            price=700000,
            description='A second listing.',
            status=Property.Status.AVAILABLE,
            publication_status=Property.PublicationStatus.PUBLISHED,
        )

        response = self.client.get(reverse('api:property-list'), {'page_size': 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 1)


class ManagedPropertyApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username='crud-owner')
        Profile.objects.create(user=self.owner, role=Profile.Role.OWNER)
        self.other_owner = user_model.objects.create_user(username='other-owner')
        Profile.objects.create(user=self.other_owner, role=Profile.Role.OWNER)
        self.customer = user_model.objects.create_user(username='listing-customer')
        Profile.objects.create(user=self.customer, role=Profile.Role.CUSTOMER)
        self.property = Property.objects.create(
            title='Owner property',
            slug='owner-property-api',
            location='Submitted location',
            price=400000,
            description='Owner listing.',
            owner=self.owner,
            publication_status=Property.PublicationStatus.PUBLISHED,
        )

    def property_payload(self, **overrides):
        payload = {
            'title': 'New owner listing',
            'location': 'Submitted location',
            'category': 'house',
            'listing_type': 'sale',
            'price': '350000.00',
            'bedrooms': 3,
            'bathrooms': 2,
            'area_sqft': 1400,
            'description': 'New listing submitted by its owner.',
            'contact_phone': '+251900000000',
        }
        payload.update(overrides)
        return payload

    def test_owner_can_create_listing_but_cannot_publish_or_set_owner(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            reverse('api:managed-property-list'),
            self.property_payload(
                publication_status='published',
                owner_id=self.other_owner.pk,
                is_featured=True,
            ),
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        property_obj = Property.objects.get(slug=response.data['slug'])
        self.assertEqual(property_obj.owner_id, self.owner.pk)
        self.assertEqual(property_obj.publication_status, Property.PublicationStatus.PENDING_REVIEW)
        self.assertFalse(property_obj.is_featured)
        self.assertEqual(response.data['currency'], 'ETB')

    def test_owner_can_only_list_and_change_own_properties(self):
        Property.objects.create(
            title='Other owner listing',
            slug='other-owner-listing-api',
            location='Submitted location',
            price=200000,
            description='Not accessible to this owner.',
            owner=self.other_owner,
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(reverse('api:managed-property-list'))
        forbidden_detail = self.client.patch(
            reverse('api:managed-property-detail', kwargs={'pk': Property.objects.get(slug='other-owner-listing-api').pk}),
            {'title': 'Unauthorized update'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['slug'], self.property.slug)
        self.assertEqual(forbidden_detail.status_code, 404)

    def test_listing_status_and_type_must_be_compatible(self):
        self.client.force_authenticate(user=self.owner)

        invalid = self.client.patch(
            reverse('api:managed-property-detail', kwargs={'pk': self.property.pk}),
            {'status': 'rented'},
            format='json',
        )
        valid = self.client.patch(
            reverse('api:managed-property-detail', kwargs={'pk': self.property.pk}),
            {'listing_type': 'rent', 'status': 'rented'},
            format='json',
        )

        self.assertEqual(invalid.status_code, 400)
        self.assertIn('status', invalid.data['error']['details'])
        self.assertEqual(valid.status_code, 200)
        self.property.refresh_from_db()
        self.assertEqual(self.property.status, Property.Status.RENTED)

    def test_invalid_price_is_rejected_before_database_write(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            reverse('api:managed-property-list'),
            self.property_payload(price='0'),
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('price', response.data['error']['details'])
        self.assertFalse(Property.objects.filter(title='New owner listing').exists())

    def test_broker_can_create_and_manage_only_assigned_property(self):
        broker = get_user_model().objects.create_user(username='crud-broker')
        Profile.objects.create(
            user=broker,
            role=Profile.Role.BROKER,
            broker_approved=True,
        )
        PropertyBrokerAssignment.objects.create(property=self.property, broker=broker)
        self.client.force_authenticate(user=broker)

        update = self.client.patch(
            reverse('api:managed-property-detail', kwargs={'pk': self.property.pk}),
            {'status': 'inactive'},
            format='json',
        )
        created = self.client.post(
            reverse('api:managed-property-list'),
            self.property_payload(title='Broker listing'),
            format='json',
        )

        self.assertEqual(update.status_code, 200)
        self.assertEqual(created.status_code, 201)
        created_obj = Property.objects.get(slug=created.data['slug'])
        self.assertIsNone(created_obj.owner_id)
        self.assertTrue(created_obj.assigned_brokers.filter(pk=broker.pk).exists())

    def test_customer_cannot_access_listing_management(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.get(reverse('api:managed-property-list'))

        self.assertIn(response.status_code, [401, 403])

    def test_delete_removes_managed_property(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(
            reverse('api:managed-property-detail', kwargs={'pk': self.property.pk})
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Property.objects.filter(pk=self.property.pk).exists())


class PropertyImageApiTests(APITestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        settings_override = override_settings(MEDIA_ROOT=self.media_directory.name)
        settings_override.enable()
        self.addCleanup(settings_override.disable)

        owner = get_user_model().objects.create_user(username='image-owner')
        Profile.objects.create(user=owner, role=Profile.Role.OWNER)
        self.other_owner = get_user_model().objects.create_user(username='image-other-owner')
        Profile.objects.create(user=self.other_owner, role=Profile.Role.OWNER)
        self.property = Property.objects.create(
            title='Image test property',
            slug='image-test-property-api',
            location='Submitted location',
            price=400000,
            description='Image test listing.',
            owner=owner,
        )
        self.client.force_authenticate(user=owner)

    def make_image(self, name='property.png', size=(2, 2), compress_level=6):
        buffer = BytesIO()
        Image.new('RGB', size, color='green').save(
            buffer,
            format='PNG',
            compress_level=compress_level,
        )
        return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')

    def image_url(self):
        return reverse(
            'api:managed-property-images',
            kwargs={'property_id': self.property.pk},
        )

    def test_upload_validates_image_and_sets_first_image_primary(self):
        response = self.client.post(
            self.image_url(),
            {'image': self.make_image(), 'caption': 'Front view'},
            format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        image = PropertyImage.objects.get(pk=response.data['id'])
        self.assertTrue(image.is_primary)
        self.assertTrue(Path(image.image.path).is_file())

    def test_invalid_file_extension_is_rejected(self):
        response = self.client.post(
            self.image_url(),
            {
                'image': SimpleUploadedFile('document.txt', b'not an image', content_type='text/plain'),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('image', response.data['error']['details'])

    def test_image_larger_than_ten_megabytes_is_rejected(self):
        oversized_image = self.make_image(
            name='oversized.png',
            size=(2000, 2000),
            compress_level=0,
        )
        self.assertGreater(oversized_image.size, 10 * 1024 * 1024)

        response = self.client.post(
            self.image_url(),
            {'image': oversized_image},
            format='multipart',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('10 MB or smaller', str(response.data['error']['details']))

    def test_setting_a_new_primary_image_demotes_the_previous_one(self):
        first = self.client.post(
            self.image_url(),
            {'image': self.make_image(name='first.png')},
            format='multipart',
        )
        second = self.client.post(
            self.image_url(),
            {'image': self.make_image(name='second.png'), 'is_primary': True},
            format='multipart',
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertFalse(PropertyImage.objects.get(pk=first.data['id']).is_primary)
        self.assertTrue(PropertyImage.objects.get(pk=second.data['id']).is_primary)

    def test_upload_to_another_owners_property_is_not_found(self):
        other_property = Property.objects.create(
            title='Other image property',
            location='Submitted location',
            price=300000,
            description='Not managed by the caller.',
            owner=self.other_owner,
        )

        response = self.client.post(
            reverse('api:managed-property-images', kwargs={'property_id': other_property.pk}),
            {'image': self.make_image()},
            format='multipart',
        )

        self.assertEqual(response.status_code, 404)

    def test_image_can_be_deleted_with_its_stored_file(self):
        upload = self.client.post(
            self.image_url(),
            {'image': self.make_image()},
            format='multipart',
        )
        image = PropertyImage.objects.get(pk=upload.data['id'])
        stored_path = Path(image.image.path)

        response = self.client.delete(
            reverse(
                'api:managed-property-image-detail',
                kwargs={'property_id': self.property.pk, 'pk': image.pk},
            )
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(PropertyImage.objects.filter(pk=image.pk).exists())
        self.assertFalse(stored_path.exists())

    def test_deleting_property_removes_its_stored_images(self):
        upload = self.client.post(
            self.image_url(),
            {'image': self.make_image()},
            format='multipart',
        )
        image = PropertyImage.objects.get(pk=upload.data['id'])
        stored_path = Path(image.image.path)

        response = self.client.delete(
            reverse('api:managed-property-detail', kwargs={'pk': self.property.pk})
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Property.objects.filter(pk=self.property.pk).exists())
        self.assertFalse(stored_path.exists())

    def test_image_limit_is_enforced(self):
        for index in range(10):
            self.property.images.create(image=self.make_image(name=f'image-{index}.png'))

        response = self.client.post(
            self.image_url(),
            {'image': self.make_image(name='eleventh.png')},
            format='multipart',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('image', response.data['error']['details'])
        self.assertEqual(self.property.images.count(), 10)
