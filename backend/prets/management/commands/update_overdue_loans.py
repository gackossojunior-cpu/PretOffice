from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef
from django.utils import timezone

from prets.models import Installment, Loan
from prets.views import update_loan_status


class Command(BaseCommand):
    help = "Marque en retard les prêts actifs ayant une échéance impayée."

    def handle(self, *args, **options):
        today = timezone.localdate()
        overdue_installments = Installment.objects.filter(
            loan_id=OuterRef("pk"),
            due_date__lt=today,
        ).exclude(status="PAID")
        loans = Loan.objects.filter(
            status="ACTIVE",
        ).filter(
            Exists(overdue_installments),
        )
        updated_count = 0
        for loan in loans.iterator():
            update_loan_status(loan)
            if loan.status == "OVERDUE":
                updated_count += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"{updated_count} prêt(s) marqué(s) en retard."
            )
        )
