from rest_framework import serializers

from owner_announcements.models import InAppNotification


class InAppNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InAppNotification
        fields = ['id', 'notification_type', 'message', 'announcement_id', 'read_at', 'created_at']
