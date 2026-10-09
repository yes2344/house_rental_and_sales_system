from django.conf import settings
from django.db import models

from properties.models import Property


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'property'], name='favorite_user_property_unique'),
        ]
        indexes = [
            models.Index(fields=['user', '-created_at'], name='favorite_user_created_idx'),
        ]

    def __str__(self):
        return f'{self.user} favorited {self.property}'
