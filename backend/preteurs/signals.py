from django.db.models.signals import post_save
from django.dispatch import receiver

from comptes.models import User
from .models import LenderProfile


@receiver(post_save, sender=User)
def create_lender_profile(sender, instance, created, **kwargs):
    if created and instance.role == "LENDER":
        LenderProfile.objects.create(user=instance, phone=instance.phone or "",)