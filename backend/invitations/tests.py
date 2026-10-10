from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from emprunteurs.models import Borrower
from audit.models import AuditEvent
from .models import Invitations


User = get_user_model()


class InvitationAndBorrowerAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.lender_a = User.objects.create_user(
            username="invitation_lender_a",
            email="invitation_lender_a@example.invalid",
            password="Safe-Test-Password-739!",
            role="LENDER",
            first_name="Lender",
            last_name="A",
        )
        self.lender_b = User.objects.create_user(
            username="invitation_lender_b",
            email="invitation_lender_b@example.invalid",
            password="Safe-Test-Password-739!",
            role="LENDER",
        )
        self.borrower_a = Borrower.objects.create(
            lender=self.lender_a,
            first_name="Borrower",
            last_name="A",
            phone="0000000001",
        )
        self.invitation_a = Invitations.objects.create(
            lender=self.lender_a,
            expires_at=timezone.now() + timedelta(days=7),
        )

    def test_lender_can_create_list_and_revoke_own_invitation(self):
        self.client.force_authenticate(user=self.lender_a)

        create_response = self.client.post("/api/invitations/", {}, format="json")
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(create_response.data["invitation_url"].startswith("http"))

        invitation = Invitations.objects.get(pk=create_response.data["id"])
        self.assertEqual(invitation.lender, self.lender_a)
        self.assertEqual(invitation.status, "PENDING")
        self.assertGreater(invitation.expires_at, timezone.now())

        list_response = self.client.get("/api/invitations/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data["results"]), 2)

        detail_response = self.client.get(
            f"/api/invitations/{self.invitation_a.pk}/"
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        revoke_response = self.client.post(
            f"/api/invitations/{self.invitation_a.pk}/revoke/",
            {},
            format="json",
        )
        self.assertEqual(revoke_response.status_code, status.HTTP_200_OK)
        self.invitation_a.refresh_from_db()
        self.assertEqual(self.invitation_a.status, "REVOKED")
        self.assertTrue(
            AuditEvent.objects.filter(
                actor=self.lender_a,
                action="INVITATION_REVOKED",
                object_id=str(self.invitation_a.pk),
            ).exists()
        )

    def test_lender_cannot_access_another_lenders_invitation_or_borrower(self):
        self.client.force_authenticate(user=self.lender_b)

        invitation_response = self.client.get(
            f"/api/invitations/{self.invitation_a.pk}/"
        )
        revoke_response = self.client.post(
            f"/api/invitations/{self.invitation_a.pk}/revoke/",
            {},
            format="json",
        )
        borrower_response = self.client.get(
            f"/api/borrowers/{self.borrower_a.pk}/"
        )
        borrower_patch = self.client.patch(
            f"/api/borrowers/{self.borrower_a.pk}/",
            {"first_name": "Tampered"},
            format="json",
        )

        self.assertEqual(invitation_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(revoke_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(borrower_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(borrower_patch.status_code, status.HTTP_404_NOT_FOUND)
        self.borrower_a.refresh_from_db()
        self.assertEqual(self.borrower_a.first_name, "Borrower")

    def test_public_invitation_get_exposes_only_validity_and_lender_name(self):
        response = self.client.get(
            f"/api/invitations/public/{self.invitation_a.token}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data),
            {"is_valid", "lender_name"},
        )
        self.assertTrue(response.data["is_valid"])
        self.assertEqual(response.data["lender_name"], "Lender A")

    def test_public_application_is_single_use_and_invalid_tokens_are_generic(self):
        data = {
            "first_name": "New",
            "last_name": "Borrower",
            "phone": "0000000003",
        }
        url = f"/api/invitations/public/{self.invitation_a.token}/"

        first_response = self.client.post(url, data, format="json")
        second_response = self.client.post(url, data, format="json")
        invalid_response = self.client.post(
            "/api/invitations/public/not-a-real-token/",
            data,
            format="json",
        )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(invalid_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(second_response.data, invalid_response.data)
        self.invitation_a.refresh_from_db()
        self.assertEqual(self.invitation_a.status, "USED")
        self.assertIsNotNone(self.invitation_a.used_at)
        borrower = Borrower.objects.get(pk=first_response.data["borrower_id"])
        self.assertEqual(borrower.lender, self.lender_a)

    def test_expired_and_revoked_public_tokens_have_same_response(self):
        expired = Invitations.objects.create(
            lender=self.lender_a,
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        revoked = Invitations.objects.create(
            lender=self.lender_a,
            status="REVOKED",
            expires_at=timezone.now() + timedelta(days=7),
        )

        expired_response = self.client.get(
            f"/api/invitations/public/{expired.token}/"
        )
        revoked_response = self.client.get(
            f"/api/invitations/public/{revoked.token}/"
        )

        self.assertEqual(expired_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(revoked_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(expired_response.data, revoked_response.data)
        expired.refresh_from_db()
        self.assertEqual(expired.status, "EXPIRED")

    def test_public_invitation_endpoint_is_throttled(self):
        url = f"/api/invitations/public/{self.invitation_a.token}/"
        responses = [self.client.get(url) for _ in range(11)]

        self.assertTrue(
            all(response.status_code == status.HTTP_200_OK for response in responses[:10])
        )
        self.assertEqual(
            responses[-1].status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )
