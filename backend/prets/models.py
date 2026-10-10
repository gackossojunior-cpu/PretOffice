from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP

from emprunteurs.models import Borrower

class LoanApplication(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "En attente"),
        ("APPROVED", "Approuvée"),
        ("REJECTED", "Rejetée"),
    )

    borrower = models.ForeignKey(
        Borrower,
        on_delete=models.CASCADE,
        related_name="loan_applications",
    )

    lender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="loan_applications",
        limit_choices_to={"role": "LENDER"},
    )

    amount_requested = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    duration_months = models.PositiveBigIntegerField()

    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Taux d'intérêt annuel en pourcentage.",
    )

    purpose = models.TextField(
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    notes = models.TextField(
        blank=True,
        null=True,
    )

    decision_reason = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta: 
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Demande de prêt de {self.borrower} à {self.lender} pour {self.amount_requested}€ sur {self.duration_months} mois "
        )


class Loan(models.Model):
    FREQUENCY_CHOICES = (
        ("WEEKLY", "Hebdomadaire"),
        ("MONTHLY", "Mensuelle"),
    )
    INTEREST_TYPE_CHOICES = (
        ("SIMPLE", "Simple"),
        ("NONE", "Sans intérêt"),
    )
    STATUS_CHOICES = (
        ("ACTIVE", "Actif"),
        ("PAID", "Remboursé"),
        ("OVERDUE", "En retard"),
        ("CANCELLED", "Annulé"),
    )
    PENALTY_TYPE_CHOICES = (
        ("RATE", "Taux"),
        ("FIXED", "Montant fixe"),
    )

    application = models.OneToOneField(
        LoanApplication,
        on_delete=models.PROTECT,
        related_name="loan",
    )
    principal_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    interest_type = models.CharField(
        max_length=10,
        choices=INTEREST_TYPE_CHOICES,
        default="SIMPLE",
    )
    duration_months = models.PositiveIntegerField()
    frequency = models.CharField(
        max_length=10,
        choices=FREQUENCY_CHOICES,
        default="MONTHLY",
    )
    disbursed_at = models.DateField(default=timezone.localdate)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="ACTIVE",
    )
    penalty_enabled = models.BooleanField(default=False)
    penalty_type = models.CharField(
        max_length=10,
        choices=PENALTY_TYPE_CHOICES,
        default="RATE",
    )
    penalty_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    penalty_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def scheduled_total_to_repay(self):
        interest = Decimal("0.00")
        if self.interest_type == "SIMPLE":
            interest = (
                self.principal_amount
                * self.interest_rate
                * Decimal(self.duration_months)
                / Decimal("1200")
            )
        return (self.principal_amount + interest).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    @property
    def total_to_repay(self):
        penalties = self.installments.aggregate(
            total=models.Sum("penalty_amount")
        )["total"] or Decimal("0.00")
        return self.scheduled_total_to_repay + penalties

    @property
    def total_paid(self):
        return self.repayments.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

    @property
    def balance_remaining(self):
        return max(self.total_to_repay - self.total_paid, Decimal("0.00"))

    @property
    def next_installment(self):
        return self.installments.exclude(status="PAID").order_by(
            "due_date",
            "number",
        ).first()

    @property
    def days_overdue(self):
        today = timezone.localdate()
        overdue_due_dates = self.installments.filter(
            due_date__lt=today,
        ).exclude(status="PAID").values_list("due_date", flat=True)
        return max(
            (today - due_date).days for due_date in overdue_due_dates
        ) if overdue_due_dates.exists() else 0

    def __str__(self):
        return f"Prêt {self.pk} - {self.application.borrower}"


class Installment(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "À payer"),
        ("PARTIAL", "Partiellement payé"),
        ("PAID", "Payé"),
        ("OVERDUE", "En retard"),
    )

    loan = models.ForeignKey(
        Loan,
        on_delete=models.CASCADE,
        related_name="installments",
    )
    number = models.PositiveIntegerField()
    due_date = models.DateField()
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    penalty_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    class Meta:
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(
                fields=("loan", "number"),
                name="unique_installment_number_per_loan",
            ),
        ]

    def __str__(self):
        return f"Échéance {self.number} du prêt {self.loan_id}"


class Repayment(models.Model):
    PAYMENT_METHOD_CHOICES = (
        ("CASH", "Espèces"),
        ("TRANSFER", "Virement"),
        ("MOBILE_MONEY", "Mobile money"),
        ("OTHER", "Autre"),
    )

    loan = models.ForeignKey(
        Loan,
        on_delete=models.PROTECT,
        related_name="repayments",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    payment_date = models.DateField(default=timezone.localdate)
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default="CASH",
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["payment_date", "created_at"]

    def __str__(self):
        return f"Remboursement {self.amount} du prêt {self.loan_id}"
    