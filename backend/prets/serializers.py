
from datetime import date
from decimal import Decimal

from django.conf import settings
from rest_framework import serializers

from emprunteurs.models import Borrower
from .models import Installment, Loan, LoanApplication, Repayment


class LoanApplicationSerializer(serializers.ModelSerializer):
    borrower = serializers.PrimaryKeyRelatedField(
        queryset=Borrower.objects.none(),
        error_messages={
            "does_not_exist": "Cet emprunteur n'est pas disponible.",
            "incorrect_type": "Cet identifiant d'emprunteur est invalide.",
        },
    )
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None and request.user.is_authenticated:
            self.fields["borrower"].queryset = Borrower.objects.filter(
                lender=request.user
            )

    def get_borrower_name(self, obj) -> str:
        return f"{obj.borrower.first_name} {obj.borrower.last_name}"

    def validate_borrower(self, value):
        request = self.context.get("request")

        if request is None:
            raise serializers.ValidationError(
                "Impossible de vérifier le prêteur connecté."
            )

        if value.lender_id != request.user.id:
            raise serializers.ValidationError(
                "Cet emprunteur n'est pas disponible."
            )

        return value


class LoanDecisionSerializer(serializers.Serializer):
    ACTION_CHOICES = (
        ("APPROVE", "Approuver"),
        ("REJECT", "Rejeter"),
    )

    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    reason = serializers.CharField()
    amount_approved = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
    )
    interest_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
    )
    duration_months = serializers.IntegerField(min_value=1, required=False)
    frequency = serializers.ChoiceField(
        choices=Loan.FREQUENCY_CHOICES,
        required=False,
        default="MONTHLY",
    )
    interest_type = serializers.ChoiceField(
        choices=Loan.INTEREST_TYPE_CHOICES,
        required=False,
        default="SIMPLE",
    )
    penalty_enabled = serializers.BooleanField(required=False, default=False)
    penalty_type = serializers.ChoiceField(
        choices=Loan.PENALTY_TYPE_CHOICES,
        required=False,
        default="RATE",
    )
    penalty_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
        default=Decimal("0.00"),
    )
    penalty_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
        default=Decimal("0.00"),
    )

    def validate(self, attrs):
        if attrs.get("interest_type") == "NONE":
            attrs["interest_rate"] = Decimal("0.00")
        if attrs.get("penalty_enabled"):
            if (
                attrs.get("penalty_type") == "RATE"
                and attrs.get("penalty_rate", Decimal("0.00")) == Decimal("0.00")
            ):
                raise serializers.ValidationError(
                    {"penalty_rate": "Indiquez un taux de pénalité supérieur à zéro."}
                )
            if (
                attrs.get("penalty_type") == "FIXED"
                and attrs.get("penalty_amount", Decimal("0.00")) == Decimal("0.00")
            ):
                raise serializers.ValidationError(
                    {"penalty_amount": "Indiquez une pénalité supérieure à zéro."}
                )
        return attrs


class LoanDecisionResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    loan_id = serializers.IntegerField(required=False)


class LoanSerializer(serializers.ModelSerializer):
    application_id = serializers.IntegerField(read_only=True)
    borrower_name = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    total_to_repay = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        read_only=True,
    )
    total_paid = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        read_only=True,
    )
    balance_remaining = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        read_only=True,
    )
    next_due_date = serializers.SerializerMethodField()
    days_overdue = serializers.IntegerField(read_only=True)
    cancelled_at = serializers.DateTimeField(read_only=True)
    cancel_reason = serializers.CharField(read_only=True)

    class Meta:
        model = Loan
        fields = (
            "id",
            "application_id",
            "borrower_name",
            "currency",
            "principal_amount",
            "interest_rate",
            "interest_type",
            "duration_months",
            "frequency",
            "disbursed_at",
            "status",
            "penalty_enabled",
            "penalty_type",
            "penalty_rate",
            "penalty_amount",
            "total_to_repay",
            "total_paid",
            "balance_remaining",
            "next_due_date",
            "days_overdue",
            "cancelled_at",
            "cancel_reason",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "application_id",
            "borrower_name",
            "currency",
            "total_to_repay",
            "total_paid",
            "balance_remaining",
            "next_due_date",
            "days_overdue",
            "cancelled_at",
            "cancel_reason",
            "created_at",
            "updated_at",
        )

    def get_borrower_name(self, obj) -> str:
        return str(obj.application.borrower)

    def get_currency(self, obj) -> str:
        return getattr(settings, "CURRENCY_CODE", "XAF")

    def get_next_due_date(self, obj) -> date | None:
        installment = obj.next_installment
        return installment.due_date if installment else None


class InstallmentSerializer(serializers.ModelSerializer):
    total_due = serializers.SerializerMethodField()

    class Meta:
        model = Installment
        fields = (
            "id",
            "number",
            "due_date",
            "amount_due",
            "amount_paid",
            "penalty_amount",
            "total_due",
            "status",
        )
        read_only_fields = fields

    def get_total_due(self, obj) -> Decimal:
        return obj.amount_due + obj.penalty_amount


class RepaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Repayment
        fields = (
            "id",
            "amount",
            "payment_date",
            "payment_method",
            "note",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class LoanCancellationSerializer(serializers.Serializer):
    reason = serializers.CharField()


class LoanCancellationResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
