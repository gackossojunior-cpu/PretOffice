from rest_framework import serializers
from .models import LenderProfile 

class LenderProfileSerializer(serializers.ModelSerializer):

    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )

    email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    first_name = serializers.CharField(
        source="user.first_name",
        read_only=True,
    )

    last_name = serializers.CharField(
        source="user.last_name",
        read_only=True,
    )

    class Meta:
        model = LenderProfile

        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "business_name",
            "business_type",
            "phone",
            "address",
            "city",
            "country",
            "is_activate",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_activate",
            "created_at",
            "updated_at",
        )