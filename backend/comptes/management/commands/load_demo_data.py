from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from emprunteurs.models import Borrower
from invitations.models import Invitations
from prets.models import Loan, LoanApplication, Repayment
from prets.views import allocate_repayment, generate_installments, update_loan_status


User = get_user_model()


class Command(BaseCommand):
    help = "Crée des données de démonstration pour deux prêteurs."

    def handle(self, *args, **options):
        lenders = []
        for suffix, first_name in (("a", "Aline"), ("b", "Boris")):
            lender, created = User.objects.get_or_create(
                username=f"demo_lender_{suffix}",
                defaults={
                    "email": f"demo_lender_{suffix}@example.invalid",
                    "first_name": first_name,
                    "last_name": "Démo",
                    "role": "LENDER",
                },
            )
            if created:
                lender.set_unusable_password()
                lender.save(update_fields=("password",))
            lenders.append(lender)

        for lender, suffix in zip(lenders, ("A", "B")):
            self.create_lender_data(lender, suffix)

        self.stdout.write(
            self.style.SUCCESS(
                "Données de démonstration prêtes pour deux prêteurs. "
                "Les comptes démo n'ont pas de mot de passe utilisable."
            )
        )

    def create_lender_data(self, lender, suffix):
        borrowers = []
        for index in range(1, 3):
            borrower, _ = Borrower.objects.get_or_create(
                lender=lender,
                first_name=f"Emprunteur {suffix}{index}",
                last_name="Démo",
                defaults={
                    "phone": f"0000000{suffix}{index}",
                    "email": f"borrower_{suffix.lower()}{index}@example.invalid",
                },
            )
            borrowers.append(borrower)

        if not Invitations.objects.filter(
            lender=lender,
            status="PENDING",
            expires_at__gt=timezone.now(),
        ).exists():
            Invitations.objects.create(
                lender=lender,
                expires_at=timezone.now() + timedelta(days=7),
            )

        for index, borrower in enumerate(borrowers, start=1):
            application, _ = LoanApplication.objects.get_or_create(
                lender=lender,
                borrower=borrower,
                defaults={
                    "amount_requested": Decimal("1000.00") * index,
                    "duration_months": 12,
                    "interest_rate": Decimal("5.00"),
                    "status": "APPROVED",
                    "decision_reason": "Accord de démonstration",
                },
            )
            loan, created = Loan.objects.get_or_create(
                application=application,
                defaults={
                    "principal_amount": application.amount_requested,
                    "interest_rate": application.interest_rate,
                    "duration_months": application.duration_months,
                    "frequency": "MONTHLY",
                },
            )
            if created or not loan.installments.exists():
                generate_installments(loan)

            repayment, repayment_created = Repayment.objects.get_or_create(
                loan=loan,
                note="Remboursement de démonstration",
                defaults={
                    "amount": min(Decimal("100.00"), loan.total_to_repay),
                    "payment_method": "MOBILE_MONEY",
                },
            )
            if repayment_created:
                allocate_repayment(loan, repayment.amount)
                update_loan_status(loan)
