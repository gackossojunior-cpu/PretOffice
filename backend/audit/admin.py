from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "lender", "actor", "action", "object_type", "object_id")
    list_filter = ("action", "object_type", "created_at")
    search_fields = ("lender__username", "actor__username", "object_id")
    readonly_fields = ("created_at", "details")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
