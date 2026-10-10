from django.db import models

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ("ADMIN", "Administrateur"),
        ("LENDER", "Prêteur"),
        ("BORROWER", "Emprunteur"),
    )

    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="LENDER"
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

    is_email_verified = models.BooleanField(default=False)

    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return f"{self.username} - {self.role}"
