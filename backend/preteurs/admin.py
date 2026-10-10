from django.contrib import admin

from .models import LenderProfile

@admin.register(LenderProfile) 
class LenderProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "business_name",
        "business_type",
        "city",
        "country",
        "is_activate",
        "created_at",
    )

    list_filter = (
        "business_type",
        "is_activate",
        "country",
    )

    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "business_name",
        "phone",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )