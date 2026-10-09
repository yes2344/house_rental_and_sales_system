from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from favorites.models import Favorite
from favorites.serializers import FavoriteCreateSerializer, FavoriteReadSerializer


class FavoriteListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Favorite.objects.none()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False) or not self.request.user.is_authenticated:
            return Favorite.objects.none()
        return (
            Favorite.objects.filter(user=self.request.user)
            .select_related('property')
            .prefetch_related('property__images', 'property__amenities')
        )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return FavoriteCreateSerializer
        return FavoriteReadSerializer

    @extend_schema(
        summary='List the authenticated user’s favorites',
        responses=FavoriteReadSerializer(many=True),
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='Favorite a published available property',
        request=FavoriteCreateSerializer,
        responses={201: FavoriteReadSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        favorite = serializer.save(user=request.user)
        output = FavoriteReadSerializer(favorite, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)


class FavoriteDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Favorite.objects.all()
    serializer_class = FavoriteReadSerializer
    lookup_field = 'property_id'
    lookup_url_kwarg = 'property_id'

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False) or not self.request.user.is_authenticated:
            return Favorite.objects.none()
        return Favorite.objects.filter(user=self.request.user)
