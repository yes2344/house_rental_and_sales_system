from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from favorites.models import Favorite
from properties.models import Property


class FavoriteConstraintTests(TestCase):
    def test_user_cannot_favorite_same_property_twice(self):
        user = get_user_model().objects.create_user(username='favorite-customer')
        property_obj = Property.objects.create(
            title='Favorite Test Property',
            location='Submitted location',
            price=100000,
            description='A test listing.',
        )
        Favorite.objects.create(user=user, property=property_obj)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Favorite.objects.create(user=user, property=property_obj)


class FavoriteApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='favorites-api-user')
        self.other_user = user_model.objects.create_user(username='favorites-other-user')
        self.property = Property.objects.create(
            title='Favorite API property',
            slug='favorite-api-property',
            location='Submitted location',
            price=200000,
            description='A public listing.',
            publication_status=Property.PublicationStatus.PUBLISHED,
            status=Property.Status.AVAILABLE,
        )
        self.other_property = Property.objects.create(
            title='Other favorite API property',
            slug='other-favorite-api-property',
            location='Submitted location',
            price=300000,
            description='Another public listing.',
            publication_status=Property.PublicationStatus.PUBLISHED,
            status=Property.Status.AVAILABLE,
        )

    def test_authenticated_user_can_add_list_and_remove_favorite(self):
        self.client.force_authenticate(user=self.user)

        added = self.client.post(
            reverse('api:favorite-list'),
            {'property_id': self.property.pk},
            format='json',
        )
        listed = self.client.get(reverse('api:favorite-list'))
        removed = self.client.delete(
            reverse('api:favorite-delete', kwargs={'property_id': self.property.pk})
        )

        self.assertEqual(added.status_code, 201)
        self.assertEqual(added.data['property']['slug'], self.property.slug)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data['count'], 1)
        self.assertEqual(removed.status_code, 204)
        self.assertFalse(Favorite.objects.filter(user=self.user, property=self.property).exists())

    def test_duplicate_favorite_is_idempotent(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('api:favorite-list')
        payload = {'property_id': self.property.pk}

        first = self.client.post(url, payload, format='json')
        second = self.client.post(url, payload, format='json')

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.data['id'], second.data['id'])
        self.assertEqual(Favorite.objects.filter(user=self.user).count(), 1)

    def test_favorites_are_isolated_between_users(self):
        Favorite.objects.create(user=self.user, property=self.property)
        Favorite.objects.create(user=self.other_user, property=self.other_property)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('api:favorite-list'))

        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['property']['slug'], self.property.slug)

    def test_unavailable_property_cannot_be_favorited(self):
        self.property.status = Property.Status.SOLD
        self.property.save()
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse('api:favorite-list'),
            {'property_id': self.property.pk},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('property_id', response.data['error']['details'])

    def test_favorites_require_authentication(self):
        response = self.client.get(reverse('api:favorite-list'))

        self.assertIn(response.status_code, [401, 403])
