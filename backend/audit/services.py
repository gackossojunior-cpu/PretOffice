from audit.models import AuditEvent


def record_audit_event(actor, action, obj, details=None):
    return AuditEvent.objects.create(
        actor=actor,
        lender=actor,
        action=action,
        object_type=obj._meta.label,
        object_id=str(obj.pk),
        details=details or {},
    )
