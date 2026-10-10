from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from emprunteurs.models import Borrower
from invitations.models import Invitations
from prets.models import Installment, Loan, LoanApplication, Repayment


User = get_user_model()


class DemoDataCommandTests(TestCase):
    def test_demo_command_is_idempotent(self):
        call_command("load_demo_data", verbosity=0)
        call_command("load_demo_data", verbosity=0)

        demo_lenders = User.objects.filter(username__startswith="demo_lender_")
        self.assertEqual(demo_lenders.count(), 2)
        self.assertEqual(Borrower.objects.filter(lender__in=demo_lenders).count(), 4)
        self.assertEqual(Invitations.objects.filter(lender__in=demo_lenders).count(), 2)
        self.assertEqual(
            LoanApplication.objects.filter(lender__in=demo_lenders).count(),
            4,
        )
        self.assertEqual(Loan.objects.filter(application__lender__in=demo_lenders).count(), 4)
        self.assertGreater(
            Installment.objects.filter(loan__application__lender__in=demo_lenders).count(),
            0,
        )
        self.assertEqual(
            Repayment.objects.filter(loan__application__lender__in=demo_lenders).count(),
            4,
        )
