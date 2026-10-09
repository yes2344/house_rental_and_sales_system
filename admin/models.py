from django.conf import settings
from django.db import models


class AdminAuditEvent(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='admin_audit_events',
        null=True,
        blank=True,
    )
    actor_username = models.CharField(max_length=150)
    action = models.CharField(max_length=50)
    object_type = models.CharField(max_length=50)
    object_id = models.CharField(max_length=64)
    changes = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['object_type', 'object_id'], name='admin_audit_object_idx'),
            models.Index(fields=['-created_at'], name='admin_audit_created_idx'),
        ]

    def __str__(self):
        return f'{self.action}: {self.object_type} {self.object_id}'
