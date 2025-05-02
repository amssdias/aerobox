import unittest

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.features.factories.feature import FeatureFactory
from apps.subscriptions.factories.plan_factory import PlanFactory
from apps.subscriptions.factories.plan_feature import PlanFeatureFactory


class PlanListAPIViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()
        cls.list_url = reverse("plan-list")

        # Create test plans using PlanFactory
        cls.plan1 = PlanFactory(is_active=True)
        cls.plan2 = PlanFactory(is_active=True)
        cls.plan3 = PlanFactory(is_active=False)

        # Create test features
        cls.feature = FeatureFactory(name="Cloud Storage", description="Store files securely")

        # Link features to the plan with metadata
        cls.plan_feature1 = PlanFeatureFactory(plan=cls.plan1, feature=cls.feature, metadata={"storage_limit_gb": 100})
        cls.plan_feature2 = PlanFeatureFactory(plan=cls.plan2, feature=cls.feature, metadata={"priority": True})

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
            self.assertIn("features", plan)

    def test_plan_with_no_description(self):
        plan = PlanFactory(description={}, is_active=True)
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data), 3)

        for p in response.data:
            if p["name"] == plan.name:
                self.assertEqual({}, p["description"])

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

    def test_only_get_method_allowed(self):
        post_response = self.client.post(self.list_url, {})
        self.assertEqual(post_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        put_response = self.client.put(self.list_url, {})
        self.assertEqual(put_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        delete_response = self.client.delete(self.list_url)
        self.assertEqual(delete_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_plan_contains_features(self):
        response = self.client.get(self.list_url)
        for plan in response.data:
            if plan["name"] == self.plan1.name:
                self.assertEqual(len(plan["features"]), 1)

    def test_feature_fields_in_response(self):
        response = self.client.get(self.list_url)
        for plan in response.data:
            for feature in plan["features"]:
                self.assertIn("name", feature)
                self.assertIn("description", feature)
                self.assertIn("metadata", feature)

    def test_feature_values_are_correct(self):
        response = self.client.get(self.list_url)
        for plan in response.data:
            feature_names = [feature["name"] for feature in plan["features"]]
            self.assertIn(self.feature.name, feature_names)

    @unittest.skip("Skipping: Metadata not defined yet.")
    def test_feature_metadata_is_correct(self):
        response = self.client.get(self.list_url)
        for plan in response.data:
            if plan["name"] == self.plan.name:
                for feature in plan["features"]:
                    if feature["name"] == self.feature.name:
                        self.assertEqual(feature["metadata"]["storage_limit_gb"], 100)
                    elif feature["name"] == self.feature.name:
                        self.assertEqual(feature["metadata"]["priority"], True)

    def test_plan_with_no_features(self):
        plan_no_features = PlanFactory(name="No Features", is_active=True)
        response = self.client.get(self.list_url)
        for plan in response.data:
            if plan["name"] == plan_no_features.name:
                self.assertEqual(plan["features"], [])

    @unittest.skip("Skipping: Metadata not defined yet.")
    def test_plan_with_feature_but_no_metadata(self):
        feature_no_metadata = FeatureFactory(name="Basic Feature")
        PlanFeatureFactory(plan=self.plan1, feature=feature_no_metadata, metadata={})  # Empty metadata
        response = self.client.get(self.list_url)
        for plan in response.data:
            if plan["name"] == self.plan1.name:
                for feature in plan["features"]:
                    if feature["name"] == feature_no_metadata.name:
                        self.assertEqual(feature["metadata"], {})
