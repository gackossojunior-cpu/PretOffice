from django.db import models
from django.conf import settings

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
    