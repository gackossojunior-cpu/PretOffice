from django.contrib import admin

from .models import Invitations


@admin.register(Invitations)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("id", "lender", "status", "created_at", "expires_at", "used_at")
    list_filter = ("status", "created_at", "expires_at")
    search_fields = ("token", "lender__username")
    readonly_fields = ("token", "created_at", "used_at")

    def has_delete_permission(self, request, obj=None):
        return False
