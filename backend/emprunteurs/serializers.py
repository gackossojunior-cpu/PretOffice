from rest_framework import serializers
from .models import Borrower


class BorrowerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrower
        fields = (
            "id",
            "first_name",
            "last_name",
            "phone",
            "email",
            "address",
            "national_id",
            "occupation",
            "proof_of_address",
            "created_at",
            "update_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "update_at",
        )


class PublicBorrowerApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        fields = (
            "first_name",
            "last_name",
            "phone",
            "email",
            "address",
            "national_id",
            "occupation",
            "proof_of_address",
        )

    def validate_proof_of_address(self, value):
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError(
                "Le certificat de domiciliation ne doit pas dépasser 5 Mo."
            )
        allowed_types = [
            "image/jpeg",
            "image/png",
            "image/webp",
        ]

        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                "Le certificat doit être une image JPEG, PNG ou WebP"
            )
        return value