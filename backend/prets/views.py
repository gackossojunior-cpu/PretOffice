import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_DOWN

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from config.mixins import LenderScopedQuerysetMixin, lender_scoped_queryset
from config.pagination import paginated_response
from audit.services import record_audit_event
from preteurs.permissions import HasLenderProfile

from .models import Installment, Loan, LoanApplication, Repayment
from .serializers import (
    InstallmentSerializer,
    LoanCancellationSerializer,
    LoanCancellationResponseSerializer,
    LoanDecisionSerializer,
    LoanDecisionResponseSerializer,
    LoanApplicationSerializer,
    LoanSerializer,
    RepaymentSerializer,
)


LOAN_LENDER_FILTERS = (
    "application__lender",
    "application__borrower__lender",
)


class LoanApplicationListCreateView(
    LenderScopedQuerysetMixin,
    generics.ListCreateAPIView,
):
    serializer_class = LoanApplicationSerializer
    permission_classes = [permissions.IsAuthenticated, HasLenderProfile]
    queryset = LoanApplication.objects.all()
    lender_filter_fields = ("lender", "borrower__lender")
    query_filter_fields = {
        "status": "status",
        "borrower": "borrower_id",
        "created_after": "created_at__date__gte",
        "created_before": "created_at__date__lte",
    }
    ordering_fields = ("created_at", "amount_requested", "status", "id")
    default_ordering = ("-created_at",)

    def perform_create(self, serializer):
        serializer.save(lender=self.request.user)


class LoanDecisionView(LenderScopedQuerysetMixin, APIView):
    permission_classes = [permissions.IsAuthenticated, HasLenderProfile]
    lender_filter_fields = ("lender", "borrower__lender")

    @transaction.atomic
    @extend_schema(
        request=LoanDecisionSerializer,
        responses=LoanDecisionResponseSerializer,
    )
    def post(self, request, pk):
        try:
            application = lender_scoped_queryset(
                LoanApplication.objects.select_for_update(),
                request.user,
                self.lender_filter_fields,
            ).get(pk=pk)
        except LoanApplication.DoesNotExist as exc:
            raise NotFound("Demande de prêt non trouvée.") from exc

        serializer = LoanDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if application.status != "PENDING":
            return Response(
                {"detail": "La demande de prêt a déjà été traitée."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        application.status = (
            "APPROVED" if data["action"] == "APPROVE" else "REJECTED"
        )
        application.decision_reason = data.get("reason", "")
        application.save(update_fields=("status", "decision_reason", "updated_at"))

        response_data = {
            "detail": (
                "Demande de prêt approuvée."
                if data["action"] == "APPROVE"
                else "Demande de prêt rejetée."
            )
        }
        if data["action"] == "APPROVE":
            interest_type = data["interest_type"]
            interest_rate = (
                Decimal("0.00")
                if interest_type == "NONE"
                else data.get("interest_rate", application.interest_rate)
            )
            loan = Loan.objects.create(
                application=application,
                principal_amount=data.get(
                    "amount_approved",
                    application.amount_requested,
                ),
                interest_rate=interest_rate,
                interest_type=interest_type,
                duration_months=data.get(
                    "duration_months",
                    application.duration_months,
                ),
                frequency=data["frequency"],
                penalty_enabled=data["penalty_enabled"],
                penalty_type=data["penalty_type"],
                penalty_rate=data["penalty_rate"],
                penalty_amount=data["penalty_amount"],
            )
            generate_installments(loan)
            response_data["loan_id"] = loan.pk

        record_audit_event(
            request.user,
            f"LOAN_{application.status}",
            application,
            {"loan_id": response_data.get("loan_id")},
        )
        return Response(response_data, status=status.HTTP_200_OK)


class LoanDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasLenderProfile]
    serializer_class = LoanSerializer

    @extend_schema(responses=LoanSerializer)
    def get(self, request, pk):
        loan = get_owned_loan(request.user, pk)
        update_loan_status(loan)
        return Response(LoanSerializer(loan).data)


class LoanInstallmentsView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasLenderProfile]
    serializer_class = InstallmentSerializer

    @extend_schema(responses=InstallmentSerializer(many=True))
    def get(self, request, pk):
        loan = get_owned_loan(request.user, pk)
        update_loan_status(loan)
        return paginated_response(
            request,
            loan.installments.all(),
            InstallmentSerializer,
            {
                "status": "status",
                "due_after": "due_date__gte",
                "due_before": "due_date__lte",
            },
            ("number", "due_date", "amount_due", "status"),
            ("number",),
        )


class LoanRepaymentsView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasLenderProfile]
    serializer_class = RepaymentSerializer

    @extend_schema(responses=RepaymentSerializer(many=True))
    def get(self, request, pk):
        loan = get_owned_loan(request.user, pk)
        update_loan_status(loan)
        return paginated_response(
            request,
            loan.repayments.all(),
            RepaymentSerializer,
            {
                "payment_method": "payment_method",
                "payment_after": "payment_date__gte",
                "payment_before": "payment_date__lte",
            },
            ("payment_date", "amount", "created_at"),
            ("payment_date", "created_at"),
        )

    @transaction.atomic
    @extend_schema(
        request=RepaymentSerializer,
        responses=RepaymentSerializer,
    )
    def post(self, request, pk):
        loan = get_owned_loan(request.user, pk, lock=True)
        update_loan_status(loan)
        if loan.status not in ("ACTIVE", "OVERDUE"):
            raise ValidationError(
                {"detail": "Ce prêt ne peut plus recevoir de remboursement."}
            )

        serializer = RepaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        if amount > loan.balance_remaining:
            raise ValidationError(
                {"amount": "Le montant dépasse le solde restant dû."}
            )

        repayment: Repayment = serializer.save(loan=loan)
        allocate_repayment(loan, amount)
        update_loan_status(loan)
        record_audit_event(
            request.user,
            "REPAYMENT_CREATED",
            repayment,
            {
                "loan_id": loan.pk,
                "amount": str(repayment.amount),
                "payment_method": repayment.payment_method,
            },
        )
        return Response(
            RepaymentSerializer(repayment).data,
            status=status.HTTP_201_CREATED,
        )


class LoanCancellationView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasLenderProfile]

    @transaction.atomic
    @extend_schema(
        request=LoanCancellationSerializer,
        responses=LoanCancellationResponseSerializer,
    )
    def post(self, request, pk):
        loan = get_owned_loan(request.user, pk, lock=True)
        serializer = LoanCancellationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if loan.status not in ("ACTIVE", "OVERDUE"):
            raise ValidationError(
                {"detail": "Ce prêt ne peut pas être annulé."}
            )
        if loan.repayments.exists():
            raise ValidationError(
                {
                    "detail": (
                        "Un prêt ayant reçu un remboursement ne peut pas être "
                        "annulé."
                    )
                }
            )

        loan.status = "CANCELLED"
        loan.cancelled_at = timezone.now()
        loan.cancel_reason = serializer.validated_data["reason"]
        loan.save(
            update_fields=(
                "status",
                "cancelled_at",
                "cancel_reason",
                "updated_at",
            )
        )
        record_audit_event(
            request.user,
            "LOAN_CANCELLED",
            loan,
            {"reason": loan.cancel_reason},
        )
        return Response(
            {"detail": "Prêt annulé."},
            status=status.HTTP_200_OK,
        )


def get_owned_loan(user, pk, lock=False):
    queryset = lender_scoped_queryset(
        Loan.objects.select_related(
            "application",
            "application__borrower",
        ),
        user,
        LOAN_LENDER_FILTERS,
    )
    if lock:
        queryset = queryset.select_for_update()

    try:
        return queryset.get(pk=pk)
    except Loan.DoesNotExist as exc:
        raise NotFound("Prêt non trouvé.") from exc


def generate_installments(loan):
    if loan.frequency == "MONTHLY":
        count = loan.duration_months
    else:
        count = (loan.duration_months * 52 + 11) // 12

    scheduled_total = loan.scheduled_total_to_repay
    amount_per_installment = (
        scheduled_total / count
    ).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    final_amount = scheduled_total - amount_per_installment * (count - 1)
    installments = []

    for number in range(1, count + 1):
        if loan.frequency == "MONTHLY":
            due_date = add_months(loan.disbursed_at, number)
        else:
            due_date = loan.disbursed_at + timedelta(weeks=number)
        installments.append(
            Installment(
                loan=loan,
                number=number,
                due_date=due_date,
                amount_due=(
                    final_amount if number == count else amount_per_installment
                ),
            )
        )

    Installment.objects.bulk_create(installments)


def add_months(value: date, months: int):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def update_loan_status(loan):
    if loan.status == "CANCELLED":
        return

    today = timezone.localdate()
    overdue_installments = loan.installments.filter(
        due_date__lt=today,
        status__in=("PENDING", "PARTIAL"),
    )
    for installment in overdue_installments:
        fields = ["status"]
        installment.status = "OVERDUE"
        if loan.penalty_enabled and installment.penalty_amount == Decimal("0.00"):
            if loan.penalty_type == "FIXED":
                penalty = loan.penalty_amount
            else:
                penalty = (
                    installment.amount_due
                    * loan.penalty_rate
                    / Decimal("100")
                ).quantize(Decimal("0.01"))
            installment.penalty_amount = penalty
            fields.append("penalty_amount")
        installment.save(update_fields=fields)
    loan.installments.filter(
        due_date__gte=today,
        status="OVERDUE",
        amount_paid=Decimal("0.00"),
    ).update(status="PENDING")
    loan.installments.filter(
        due_date__gte=today,
        status="OVERDUE",
    ).exclude(amount_paid=Decimal("0.00")).update(status="PARTIAL")

    if loan.balance_remaining <= Decimal("0.00"):
        new_status = "PAID"
    elif loan.days_overdue > 0:
        new_status = "OVERDUE"
    else:
        new_status = "ACTIVE"

    if loan.status != new_status:
        loan.status = new_status
        loan.save(update_fields=("status", "updated_at"))


def allocate_repayment(loan, amount):
    amount_remaining = amount
    today = timezone.localdate()

    for installment in loan.installments.exclude(status="PAID").order_by(
        "due_date",
        "number",
    ).select_for_update():
        installment_total = installment.amount_due + installment.penalty_amount
        installment_balance = installment_total - installment.amount_paid
        applied_amount = min(installment_balance, amount_remaining)
        installment.amount_paid += applied_amount
        amount_remaining -= applied_amount

        if installment.amount_paid >= installment_total:
            installment.status = "PAID"
        elif installment.due_date < today:
            installment.status = "OVERDUE"
        else:
            installment.status = "PARTIAL"

        installment.save(update_fields=("amount_paid", "status"))
        if amount_remaining <= Decimal("0.00"):
            break
