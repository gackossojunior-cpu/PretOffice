from django.contrib import admin

from .models import Borrower


@admin.register(Borrower)
class BorrowerAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "phone", "lender", "created_at")
    list_filter = ("created_at",)
    search_fields = ("first_name", "last_name", "phone", "email", "lender__username")
    readonly_fields = ("created_at", "update_at")

    def has_delete_permission(self, request, obj=None):
        return False
