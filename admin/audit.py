from admin.models import AdminAuditEvent


def record_admin_action(actor, *, action, object_type, object_id, changes):
    AdminAuditEvent.objects.create(
        actor=actor,
        actor_username=actor.get_username(),
        action=action,
        object_type=object_type,
        object_id=str(object_id),
        changes=changes,
    )
