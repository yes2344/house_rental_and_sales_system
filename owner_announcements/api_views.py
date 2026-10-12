from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import filters, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from owner_announcements.models import InAppNotification
from owner_announcements.serializers import InAppNotificationSerializer


class InAppNotificationListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InAppNotificationSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return InAppNotification.objects.filter(recipient=self.request.user).select_related('announcement')


class InAppNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(InAppNotification, pk=pk, recipient=request.user)
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=['read_at'])
        return Response(InAppNotificationSerializer(notification).data)
