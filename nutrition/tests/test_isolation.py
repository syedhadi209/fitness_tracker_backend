from datetime import date

from rest_framework.test import APIClient, APITestCase

from api.testing import authenticate, make_user
from nutrition.models import MealLog
from nutrition.services import create_meal


class MealIsolationTests(APITestCase):
    def setUp(self):
        self.alice = make_user("alice@example.com")
        self.bob = make_user("bob@example.com")
        self.bobs_meal = create_meal(
            user=self.bob,
            items=[{"description": "Steak", "calories": 500, "protein_g": 50}],
            meal_type="dinner",
            date=date(2026, 9, 20),
        )
        self.client = authenticate(APIClient(), self.alice)

    def test_list_excludes_other_users_meals(self):
        response = self.client.get("/api/nutrition/meals/")
        self.assertEqual(response.status_code, 200)
        ids = [meal["id"] for meal in response.json()["results"]]
        self.assertNotIn(self.bobs_meal.id, ids)

    def test_cannot_retrieve_another_users_meal(self):
        response = self.client.get(f"/api/nutrition/meals/{self.bobs_meal.id}/")
        self.assertEqual(response.status_code, 404)

    def test_cannot_delete_another_users_meal(self):
        response = self.client.delete(f"/api/nutrition/meals/{self.bobs_meal.id}/")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(MealLog.objects.filter(pk=self.bobs_meal.id).exists())

    def test_created_meal_is_owned_by_requesting_user(self):
        response = self.client.post(
            "/api/nutrition/meals/",
            {
                "date": "2026-09-21",
                "meal_type": "breakfast",
                "items": [
                    {
                        "description": "Oatmeal",
                        "quantity": 1,
                        "calories": 300,
                        "protein_g": 10,
                        "carbs_g": 50,
                        "fat_g": 6,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        meal = MealLog.objects.get(pk=response.json()["id"])
        self.assertEqual(meal.user, self.alice)


class AuthRequiredTests(APITestCase):
    def test_endpoints_reject_anonymous_requests(self):
        client = APIClient()
        for url in [
            "/api/nutrition/meals/",
            "/api/activity/workouts/",
            "/api/activity/steps/",
            "/api/progress/weights/",
            "/api/progress/dashboard/",
            "/api/assistant/sessions/",
        ]:
            with self.subTest(url=url):
                self.assertEqual(client.get(url).status_code, 401)

    def test_health_check_stays_public(self):
        self.assertEqual(APIClient().get("/api/health/").status_code, 200)
