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
        "user_username",
        "user_email",
        "user_first_name",
        "user_last_name",
        "business_name",
        "phone",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )