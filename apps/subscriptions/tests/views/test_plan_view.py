from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.subscriptions.factories.plan_factory import PlanFactory


class PlanListAPIViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()
        cls.list_url = reverse("plan-list")

        # Create test plans using PlanFactory
        cls.plan1 = PlanFactory(name="Basic", is_active=True)
        cls.plan2 = PlanFactory(name="Premium", is_active=True)
        cls.plan3 = PlanFactory(name="Legacy", is_active=False)

    def test_plan_list_endpoint_success(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_active_plans_only(self):
        response = self.client.get(self.list_url)

        self.assertEqual(len(response.data), 2)

        active_plans = [plan["name"] for plan in response.data]
        self.assertIn(self.plan1.name, active_plans)
        self.assertIn(self.plan2.name, active_plans)
        self.assertNotIn(self.plan3.name, active_plans)

    def test_plan_fields_in_response(self):
        response = self.client.get(self.list_url)
        for plan in response.data:
            self.assertIn("id", plan)
            self.assertIn("name", plan)
            self.assertIn("description", plan)
            self.assertIn("monthly_price", plan)
            self.assertIn("yearly_price", plan)
            self.assertIn("storage_limit", plan)

    def test_plan_with_no_description(self):
        plan = PlanFactory(description=None, is_active=True)
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data), 3)

        for p in response.data:
            if p["name"] == plan.name:
                self.assertIsNone(p["description"])

    def test_empty_database(self):
        PlanFactory._meta.model.objects.all().delete()
        response = self.client.get(self.list_url)

        self.assertEqual(len(response.data), 0)

    def test_plan_prices_are_correct(self):
        response = self.client.get(self.list_url)
        for plan in response.data:
            if plan["name"] == self.plan1.name:
                self.assertEqual(plan["monthly_price"], str(self.plan1.monthly_price))
                self.assertEqual(plan["yearly_price"], str(self.plan1.yearly_price))
            elif plan["name"] == self.plan2.name:
                self.assertEqual(plan["monthly_price"], str(self.plan2.monthly_price))
                self.assertEqual(plan["yearly_price"], str(self.plan2.yearly_price))

    def test_plan_storage_limit(self):
        response = self.client.get(self.list_url)
        for plan in response.data:
            if plan["name"] == self.plan1.name:
                self.assertEqual(plan["storage_limit"], self.plan1.storage_limit)
            elif plan["name"] == self.plan2.name:
                self.assertEqual(plan["storage_limit"], self.plan2.storage_limit)

    def test_only_get_method_allowed(self):
        post_response = self.client.post(self.list_url, {})
        self.assertEqual(post_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        put_response = self.client.put(self.list_url, {})
        self.assertEqual(put_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        delete_response = self.client.delete(self.list_url)
        self.assertEqual(delete_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
