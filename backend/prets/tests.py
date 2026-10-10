from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from audit.models import AuditEvent
from django.core.management import call_command
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from emprunteurs.models import Borrower
from invitations.models import Invitations
from .models import Installment, Loan, LoanApplication, Repayment


User = get_user_model()


class LenderIsolationAPITests(APITestCase):
    def setUp(self):
        self.password = "Safe-Test-Password-739!"
        self.lender_a = User.objects.create_user(
            username="lender_a",
            email="lender_a@example.invalid",
            password=self.password,
            role="LENDER",
        )
        self.lender_b = User.objects.create_user(
            username="lender_b",
            email="lender_b@example.invalid",
            password=self.password,
            role="LENDER",
        )
        self.borrower_a = Borrower.objects.create(
            lender=self.lender_a,
            first_name="Emprunteur",
            last_name="A",
            phone="0000000001",
        )
        self.borrower_b = Borrower.objects.create(
            lender=self.lender_b,
            first_name="Emprunteur",
            last_name="B",
            phone="0000000002",
        )
        self.invitation_a = Invitations.objects.create(
            lender=self.lender_a,
            expires_at=timezone.now() + timedelta(days=7),
        )
        self.loan_a = LoanApplication.objects.create(
            borrower=self.borrower_a,
            lender=self.lender_a,
            amount_requested="1000.00",
            duration_months=12,
            interest_rate="5.00",
        )

    def test_lender_b_cannot_list_lender_a_records(self):
        self.client.force_authenticate(user=self.lender_b)

        borrowers = self.client.get("/api/borrowers/")
        invitations = self.client.get("/api/invitations/")
        loans = self.client.get("/api/loans/")

        self.assertEqual(borrowers.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in borrowers.data["results"]],
            [self.borrower_b.pk],
        )
        self.assertNotIn(
            self.borrower_a.pk,
            [item["id"] for item in borrowers.data["results"]],
        )
        self.assertEqual(invitations.status_code, status.HTTP_200_OK)
        self.assertEqual(invitations.data["results"], [])
        self.assertEqual(loans.status_code, status.HTTP_200_OK)
        self.assertEqual(loans.data["results"], [])

    def test_lender_b_cannot_create_loan_for_lender_a_borrower(self):
        self.client.force_authenticate(user=self.lender_b)

        response = self.client.post(
            "/api/loans/",
            {
                "borrower": self.borrower_a.pk,
                "amount_requested": "100.00",
                "duration_months": 12,
                "interest_rate": "5.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("borrower", response.data["errors"])
        self.assertEqual(
            response.data["errors"]["borrower"],
            ["Cet emprunteur n'est pas disponible."],
        )
        self.assertEqual(LoanApplication.objects.count(), 1)

    def test_list_filters_and_paginates_within_lender_scope(self):
        Borrower.objects.create(
            lender=self.lender_a,
            first_name="Second",
            last_name="Borrower",
            phone="0000000011",
        )
        self.client.force_authenticate(user=self.lender_a)

        response = self.client.get(
            "/api/borrowers/?page_size=1&ordering=first_name"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["count"], 2)

    def test_audit_event_created_for_loan_decision(self):
        self.approve_application()

        event = AuditEvent.objects.get(
            actor=self.lender_a,
            action="LOAN_APPROVED",
        )
        self.assertEqual(event.lender, self.lender_a)
        self.assertEqual(event.object_id, str(self.loan_a.pk))

    def test_loan_filter_does_not_escape_lender_scope(self):
        self.client.force_authenticate(user=self.lender_b)

        response = self.client.get(
            f"/api/loans/?borrower={self.borrower_a.pk}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])

    def test_loan_lender_is_derived_from_authenticated_user(self):
        self.client.force_authenticate(user=self.lender_b)

        response = self.client.post(
            "/api/loans/",
            {
                "borrower": self.borrower_b.pk,
                "lender": self.lender_a.pk,
                "amount_requested": "200.00",
                "duration_months": 6,
                "interest_rate": "0.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        loan = LoanApplication.objects.get(pk=response.data["id"])
        self.assertEqual(loan.lender, self.lender_b)

    def test_lender_b_cannot_decide_lender_a_loan(self):
        self.client.force_authenticate(user=self.lender_b)

        response = self.client.post(
            f"/api/loans/{self.loan_a.pk}/decision/",
            {"action": "APPROVE"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.loan_a.refresh_from_db()
        self.assertEqual(self.loan_a.status, "PENDING")

    def test_lender_a_can_list_own_records(self):
        self.client.force_authenticate(user=self.lender_a)

        borrowers = self.client.get("/api/borrowers/")
        invitations = self.client.get("/api/invitations/")
        loans = self.client.get("/api/loans/")

        self.assertEqual(borrowers.status_code, status.HTTP_200_OK)
        self.assertEqual(len(borrowers.data["results"]), 1)
        self.assertEqual(invitations.status_code, status.HTTP_200_OK)
        self.assertEqual(len(invitations.data["results"]), 1)
        self.assertEqual(loans.status_code, status.HTTP_200_OK)
        self.assertEqual(len(loans.data["results"]), 1)

    def approve_application(self, **terms):
        self.client.force_authenticate(user=self.lender_a)
        response = self.client.post(
            f"/api/loans/{self.loan_a.pk}/decision/",
            {
                "action": "APPROVE",
                "reason": "Accord de test",
                **terms,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return Loan.objects.get(pk=response.data["loan_id"])

    def test_approval_creates_loan_and_monthly_schedule(self):
        loan = self.approve_application(
            amount_approved="1000.00",
            interest_rate="12.00",
            duration_months=12,
            frequency="MONTHLY",
        )

        self.assertEqual(loan.total_to_repay, Decimal("1120.00"))
        self.assertEqual(loan.installments.count(), 12)
        self.assertEqual(
            sum(item.amount_due for item in loan.installments.all()),
            loan.total_to_repay,
        )
        self.loan_a.refresh_from_db()
        self.assertEqual(self.loan_a.status, "APPROVED")
        self.assertEqual(self.loan_a.decision_reason, "Accord de test")

    def test_rejection_saves_reason_without_creating_loan(self):
        self.client.force_authenticate(user=self.lender_a)

        response = self.client.post(
            f"/api/loans/{self.loan_a.pk}/decision/",
            {"action": "REJECT", "reason": "Dossier incomplet"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Loan.objects.count(), 0)
        self.loan_a.refresh_from_db()
        self.assertEqual(self.loan_a.status, "REJECTED")
        self.assertEqual(self.loan_a.decision_reason, "Dossier incomplet")

    def test_decision_requires_a_reason(self):
        self.client.force_authenticate(user=self.lender_a)

        response = self.client.post(
            f"/api/loans/{self.loan_a.pk}/decision/",
            {"action": "REJECT"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.loan_a.refresh_from_db()
        self.assertEqual(self.loan_a.status, "PENDING")

    def test_decided_application_cannot_be_decided_again(self):
        self.approve_application()

        response = self.client.post(
            f"/api/loans/{self.loan_a.pk}/decision/",
            {"action": "REJECT"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Loan.objects.count(), 1)

    def test_loan_detail_and_related_data_are_hidden_from_other_lender(self):
        loan = self.approve_application()
        self.client.force_authenticate(user=self.lender_b)

        detail = self.client.get(f"/api/loans/{loan.pk}/")
        installments = self.client.get(f"/api/loans/{loan.pk}/installments/")
        repayments = self.client.get(f"/api/loans/{loan.pk}/repayments/")

        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(installments.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(repayments.status_code, status.HTTP_404_NOT_FOUND)

    def test_partial_full_repayment_and_overpayment_rejection(self):
        loan = self.approve_application(
            amount_approved="100.00",
            interest_type="NONE",
            duration_months=2,
        )
        self.client.force_authenticate(user=self.lender_a)
        url = f"/api/loans/{loan.pk}/repayments/"

        partial = self.client.post(
            url,
            {"amount": "20.00", "payment_method": "CASH"},
            format="json",
        )
        self.assertEqual(partial.status_code, status.HTTP_201_CREATED)
        loan.refresh_from_db()
        self.assertEqual(loan.total_paid, Decimal("20.00"))
        self.assertEqual(loan.balance_remaining, Decimal("80.00"))
        self.assertEqual(
            loan.installments.order_by("number").first().amount_paid,
            Decimal("20.00"),
        )

        overpayment = self.client.post(
            url,
            {"amount": "80.01"},
            format="json",
        )
        self.assertEqual(overpayment.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Repayment.objects.filter(loan=loan).count(), 1)

        final = self.client.post(
            url,
            {"amount": "80.00", "payment_method": "TRANSFER"},
            format="json",
        )
        self.assertEqual(final.status_code, status.HTTP_201_CREATED)
        loan.refresh_from_db()
        self.assertEqual(loan.status, "PAID")
        self.assertEqual(loan.balance_remaining, Decimal("0.00"))
        self.assertFalse(loan.installments.exclude(status="PAID").exists())

    def test_overdue_status_recalculated_and_management_command(self):
        loan = self.approve_application(
            amount_approved="100.00",
            interest_type="NONE",
            duration_months=2,
        )
        installment = loan.installments.order_by("number").first()
        past_due = timezone.localdate() - timedelta(days=3)
        Installment.objects.filter(pk=installment.pk).update(due_date=past_due)

        call_command("update_overdue_loans")
        loan.refresh_from_db()
        self.assertEqual(loan.status, "OVERDUE")

        detail = self.client.get(f"/api/loans/{loan.pk}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data["days_overdue"], 3)

    def test_weekly_schedule_and_currency_in_loan_response(self):
        loan = self.approve_application(
            amount_approved="100.00",
            interest_type="NONE",
            duration_months=12,
            frequency="WEEKLY",
        )

        self.assertEqual(loan.installments.count(), 52)
        self.client.force_authenticate(user=self.lender_a)
        response = self.client.get(f"/api/loans/{loan.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["currency"], "XAF")

    def test_fixed_late_penalty_is_applied_once_per_overdue_installment(self):
        loan = self.approve_application(
            amount_approved="100.00",
            interest_type="NONE",
            duration_months=2,
            penalty_enabled=True,
            penalty_type="FIXED",
            penalty_amount="10.00",
        )
        installment = loan.installments.order_by("number").first()
        Installment.objects.filter(pk=installment.pk).update(
            due_date=timezone.localdate() - timedelta(days=1),
        )
        self.client.force_authenticate(user=self.lender_a)

        first_read = self.client.get(f"/api/loans/{loan.pk}/")
        second_read = self.client.get(f"/api/loans/{loan.pk}/")
        loan.refresh_from_db()
        installment.refresh_from_db()

        self.assertEqual(first_read.status_code, status.HTTP_200_OK)
        self.assertEqual(second_read.status_code, status.HTTP_200_OK)
        self.assertEqual(installment.penalty_amount, Decimal("10.00"))
        self.assertEqual(loan.total_to_repay, Decimal("110.00"))
        self.assertEqual(loan.balance_remaining, Decimal("110.00"))

    def test_cancellation_is_traced_and_does_not_delete_loan(self):
        loan = self.approve_application(
            amount_approved="100.00",
            interest_type="NONE",
            duration_months=2,
        )
        self.client.force_authenticate(user=self.lender_a)

        response = self.client.post(
            f"/api/loans/{loan.pk}/cancel/",
            {"reason": "Décaissement annulé"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        loan.refresh_from_db()
        self.assertEqual(loan.status, "CANCELLED")
        self.assertEqual(loan.cancel_reason, "Décaissement annulé")
        self.assertIsNotNone(loan.cancelled_at)
        self.assertTrue(Loan.objects.filter(pk=loan.pk).exists())

    def test_loan_with_repayment_cannot_be_cancelled(self):
        loan = self.approve_application(
            amount_approved="100.00",
            interest_type="NONE",
            duration_months=2,
        )
        self.client.force_authenticate(user=self.lender_a)
        self.client.post(
            f"/api/loans/{loan.pk}/repayments/",
            {"amount": "10.00"},
            format="json",
        )

        response = self.client.post(
            f"/api/loans/{loan.pk}/cancel/",
            {"reason": "Ne doit pas aboutir"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        loan.refresh_from_db()
        self.assertEqual(loan.status, "ACTIVE")
