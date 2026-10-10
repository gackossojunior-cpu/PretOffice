from django.db import models
from django.conf import settings


class LenderProfile(models.Model):
    BUSINESS_TYPE_CHOICES = (
        ("INDIVIDUAL", "Particulier"),
        ("BUSINNESS", "Entreprise"),
        ("ORGANIZATION", "Organisation"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lender_profile",
    )

    business_name = models.CharField(
        max_length=150,
        blank=True,
    )

    business_type = models.CharField(
        max_length=20,
        choices = BUSINESS_TYPE_CHOICES,
        default = "INDIVIDUAL",
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    address = models.TextField(
        blank=True,
    )

    city = models.CharField(
        max_length=100,
        default="Congo",
    )

    country = models.CharField(
        max_length=100,
        default="Congo",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    is_activate = models.BooleanField(
        default=True,
    )

    def __str__(self):
        if self.business_name:
            return self.business_name
        
        return (
            f"{self.user.first_name} {self.user.last_name}".strip() or f"{self.user.username}"
        )