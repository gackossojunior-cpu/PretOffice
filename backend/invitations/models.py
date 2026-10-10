from django.db import models

import secrets
from django.conf import settings
from django.utils import timezone
from emprunteurs.models import Borrower

class Invitations(models.Model):
    STATUS_CHOICES = (
        ("ACTIVE", "Active"),
        ("USED", "Utilisée"),
        ("EXPIRED", "Expirée"),
        ("REVOKED", "Révoquée"),
    )

    lender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invitations",
        limit_choices_to={"role": "LENDER"},
    )

    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE",
    )

    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    used_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)

        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        if self.status != "ACTIVE":
            return False

        if timezone.now() >= self.expires_at:
            return False
        
        return True
    
    def __str__(self):
        return f"Invitations {self.id} - {self.lender.username}"

    borrower = models.OneToOneField(
        Borrower,
        on_delete=models.SET_NULL,
        related_name="invitation",
        null=True,
        blank=True,
    )
    
