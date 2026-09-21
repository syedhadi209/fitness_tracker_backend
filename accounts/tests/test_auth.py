from rest_framework.test import APIClient, APITestCase

from api.testing import authenticate, make_user


class RegistrationTests(APITestCase):
    def test_register_creates_a_user_with_a_profile(self):
        response = self.client.post(
            "/api/auth/register/",
            {"email": "new@example.com", "password": "sufficiently-long-9182"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        login = self.client.post(
            "/api/auth/login/",
            {"email": "new@example.com", "password": "sufficiently-long-9182"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn("access", login.json())

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            "/api/auth/register/",
            {"email": "weak@example.com", "password": "123"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_duplicate_email_is_rejected(self):
        make_user("taken@example.com")
        response = self.client.post(
            "/api/auth/register/",
            {"email": "taken@example.com", "password": "sufficiently-long-9182"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class MeEndpointTests(APITestCase):
    def setUp(self):
        self.user = make_user("me@example.com")
        self.client = authenticate(APIClient(), self.user)

    def test_returns_the_requesting_users_profile(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], "me@example.com")

    def test_can_update_profile_fields(self):
        response = self.client.patch(
            "/api/auth/me/",
            {"profile": {"goal": "lose", "daily_calorie_target": 2100}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.goal, "lose")
        self.assertEqual(self.user.profile.daily_calorie_target, 2100)

    def test_anonymous_request_is_rejected(self):
        self.assertEqual(APIClient().get("/api/auth/me/").status_code, 401)
