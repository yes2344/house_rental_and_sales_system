from rest_framework import serializers

from favorites.models import Favorite
from properties.access import public_properties
from properties.serializers import PublicPropertyListSerializer


class FavoriteCreateSerializer(serializers.Serializer):
    property_id = serializers.PrimaryKeyRelatedField(
        source='property',
        queryset=public_properties(),
    )

    def create(self, validated_data):
        favorite, _ = Favorite.objects.get_or_create(
            user=validated_data['user'],
            property=validated_data['property'],
        )
        return favorite


class FavoriteReadSerializer(serializers.ModelSerializer):
    property = PublicPropertyListSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ['id', 'property', 'created_at']
        read_only_fields = fields
