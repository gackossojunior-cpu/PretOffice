from django.db import models

from django.conf import settings

class Borrower(models.Model):
    lender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="borrowers",
        limit_choices_to={"role": "LENDER"},
    )

    first_name = models.CharField(
        max_length=100,
    )

    last_name = models.CharField(
        max_length=100,
    )

    phone = models.CharField(
        max_length=30,
    )

    email = models.EmailField(
        blank=True,
        null=True,
    )

    address = models.TextField(
        blank=True,
        null=True,
    )

    national_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    proof_of_address = models.ImageField(
        upload_to="borrowers/proof_of_address/",
        blank=True,
        null=True,
    )

    occupation = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    update_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
