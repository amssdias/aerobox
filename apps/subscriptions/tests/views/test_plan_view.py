from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.features.choices.feature_code_choices import FeatureCodeChoices
from apps.features.models import Feature
from apps.subscriptions.factories.plan_factory import PlanFactory
from apps.subscriptions.models import Plan


class PlanListAPIViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()
        cls.list_url = reverse("plan-list")

        # Create test plans using PlanFactory
        cls.free_plan = Plan.objects.get(is_free=True)
        cls.plan1 = PlanFactory(is_active=True)
        cls.plan2 = PlanFactory(is_active=True)
        cls.plan3 = PlanFactory(is_active=False)


    def test_plan_list_endpoint_success(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_active_plans_only(self):
        list_plans = Plan.objects.filter(is_active=True).count()
        response = self.client.get(self.list_url)

        self.assertEqual(len(response.data), list_plans)

        active_plans = [plan["name"] for plan in response.data]
        self.assertIn(self.free_plan.name, active_plans)
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
        list_plans = Plan.objects.filter(is_active=True).count()
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data), list_plans)

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
            elif plan["name"] == self.free_plan.name:
                self.assertEqual(plan["monthly_price"], str(self.free_plan.monthly_price))
                self.assertEqual(plan["yearly_price"], str(self.free_plan.yearly_price))

    def test_only_get_method_allowed(self):
        post_response = self.client.post(self.list_url, {})
        self.assertEqual(post_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        put_response = self.client.put(self.list_url, {})
        self.assertEqual(put_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        delete_response = self.client.delete(self.list_url)
        self.assertEqual(delete_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_plan_contains_features(self):
        features = Feature.objects.filter(code__in=[
            FeatureCodeChoices.CLOUD_STORAGE.value,
            FeatureCodeChoices.FILE_PREVIEW.value,
            FeatureCodeChoices.FILE_SHARING.value,
            FeatureCodeChoices.FOLDER_CREATION.value,
            FeatureCodeChoices.BASIC_SUPPORT.value,
        ]).count()
        response = self.client.get(self.list_url)
        for plan in response.data:
            if plan["name"] == self.free_plan.name:
                self.assertEqual(len(plan["features"]), features)

    def test_feature_fields_in_response(self):
        response = self.client.get(self.list_url)
        for plan in response.data:
            for feature in plan["features"]:
                self.assertIn("name", feature)
                self.assertIn("description", feature)
                self.assertIn("metadata", feature)

    def test_feature_values_are_correct(self):
        response = self.client.get(self.list_url)
        feature_codes = Feature.objects.all().values_list("code", flat=True)

        for plan in response.data:
            if plan["name"] == self.free_plan.name:
                response_feature_codes = [feature["code"] for feature in plan["features"]]
                for code in response_feature_codes:
                    self.assertIn(code, feature_codes)

    def test_feature_default_metadata_is_correct(self):
        response = self.client.get(self.list_url)
        for plan in response.data:
            if plan["name"] == self.free_plan.name:
                for feature in plan["features"]:
                    if feature["code"] == FeatureCodeChoices.CLOUD_STORAGE.value:
                        self.assertIn("max_storage_mb", feature["default_metadata"])
                        self.assertIn("max_file_size_mb", feature["default_metadata"])
                        self.assertIn("blocked_file_types", feature["default_metadata"])
                    elif feature["code"] == FeatureCodeChoices.FOLDER_CREATION.value:
                        self.assertFalse(feature["default_metadata"])
                        self.assertFalse(feature["metadata"])

    def test_plan_with_no_features(self):
        plan_no_features = PlanFactory(name="No Features", is_active=True)
        response = self.client.get(self.list_url)
        for plan in response.data:
            if plan["name"] == plan_no_features.name:
                self.assertEqual(plan["features"], [])
