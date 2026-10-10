
from rest_framework import serializers

from .models import LoanApplication


class LoanApplicationSerializer(serializers.ModelSerializer):
    borrower_name = serializers.SerializerMethodField()

    class Meta:
        model = LoanApplication
        fields = (
            "id",
            "borrower",
            "borrower_name",
            "lender",
            "amount_requested",
            "duration_months",
            "interest_rate",
            "purpose",
            "status",
            "notes",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "borrower_name",
            "lender",
            "status",
            "created_at",
            "updated_at",
        )

    def get_borrower_name(self, obj):
        return f"{obj.borrower.first_name} {obj.borrower.last_name}"

    def validate_borrower(self, value):
        request = self.context.get("request")

        if request is None:
            raise serializers.ValidationError(
                "Impossible de vérifier le prêteur connecté."
            )

        if value.lender_id != request.user.id:
            raise serializers.ValidationError(
                "Cet emprunteur n'est pas associé à votre compte prêteur."
            )

        return value
