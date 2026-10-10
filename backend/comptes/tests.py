from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from preteurs.models import LenderProfile


User = get_user_model()


class AuthenticationAPITests(APITestCase):
    def setUp(self):
        self.password = "Safe-Test-Password-739!"
        self.register_data = {
            "username": "test_lender",
            "email": "test_lender@example.invalid",
            "first_name": "Test",
            "last_name": "Lender",
            "phone": "0000000000",
            "password": self.password,
            "password_confirm": self.password,
        }

    def test_registration_creates_lender_and_profile(self):
        response = self.client.post(
            "/api/auth/register/",
            self.register_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="test_lender")
        self.assertEqual(user.role, "LENDER")
        self.assertTrue(user.check_password(self.password))
        self.assertTrue(LenderProfile.objects.filter(user=user).exists())

    def test_registration_uses_django_password_validators(self):
        data = {
            **self.register_data,
            "password": "password",
            "password_confirm": "password",
        }

        response = self.client.post("/api/auth/register/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data["errors"])
        self.assertFalse(User.objects.filter(username="test_lender").exists())

    def test_registration_rejects_duplicate_username_and_email(self):
        User.objects.create_user(
            username="existing_user",
            email="existing@example.invalid",
            password=self.password,
            role="ADMIN",
        )

        duplicate_username = {
            **self.register_data,
            "username": "existing_user",
            "email": "other@example.invalid",
        }
        response = self.client.post(
            "/api/auth/register/",
            duplicate_username,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data["errors"])

        duplicate_email = {
            **self.register_data,
            "username": "another_user",
            "email": "existing@example.invalid",
        }
        response = self.client.post(
            "/api/auth/register/",
            duplicate_email,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data["errors"])

    def test_login_refresh_and_lender_profile_patch(self):
        user = User.objects.create_user(
            username="test_lender",
            email="test_lender@example.invalid",
            password=self.password,
            role="LENDER",
        )

        login_response = self.client.post(
            "/api/auth/login/",
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", login_response.data)
        self.assertIn("refresh", login_response.data)

        refresh_response = self.client.post(
            "/api/auth/token/refresh/",
            {"refresh": login_response.data["refresh"]},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_response.data)
        self.assertIn("refresh", refresh_response.data)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
        )
        profile_response = self.client.get("/api/lenders/me/")
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)

        patch_response = self.client.patch(
            "/api/lenders/me/",
            {"business_name": "Prêteur Test"},
            format="json",
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.data["business_name"], "Prêteur Test")

    def test_lender_without_profile_gets_clear_not_found(self):
        user = User.objects.create_user(
            username="profileless_lender",
            email="profileless@example.invalid",
            password=self.password,
            role="ADMIN",
        )
        User.objects.filter(pk=user.pk).update(role="LENDER")
        user.refresh_from_db()
        self.client.force_authenticate(user=user)

        response = self.client.get("/api/lenders/me/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", response.data)

    def test_user_without_lender_profile_cannot_access_loans(self):
        user = User.objects.create_user(
            username="profileless_lender",
            email="profileless@example.invalid",
            password=self.password,
            role="ADMIN",
        )
        User.objects.filter(pk=user.pk).update(role="LENDER")
        user.refresh_from_db()
        self.client.force_authenticate(user=user)

        response = self.client.get("/api/loans/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data["detail"],
            "Un profil prêteur est requis pour accéder à cette ressource.",
        )

    def test_lender_profile_requires_authentication(self):
        response = self.client.get("/api/lenders/me/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_api_error_format_is_consistent(self):
        response = self.client.get("/api/lenders/me/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(set(response.data), {"detail", "errors"})
