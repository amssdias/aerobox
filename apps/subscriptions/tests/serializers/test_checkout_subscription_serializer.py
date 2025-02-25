from django.test import TestCase
from rest_framework.exceptions import ValidationError

from unittest.mock import patch

from apps.subscriptions.choices.subscription_choices import (
    SubscriptionBillingCycleChoices,
)
from apps.subscriptions.factories.plan_factory import PlanFactory
from apps.subscriptions.serializers.subscription import CheckoutSubscriptionSerializer
from apps.users.factories.user_factory import UserFactory


class CheckoutSubscriptionSerializerTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.monthly_plan = PlanFactory(
            name="Basic", stripe_price_id="price_123", monthly_price=10
        )
        cls.yearly_plan = PlanFactory(
            name="Premium", stripe_price_id="price_456", yearly_price=100
        )
        cls.plan_without_stripe_id = PlanFactory(
            name="Invalid Plan", stripe_price_id="", monthly_price=5
        )
        cls.plan_without_price = PlanFactory(
            name="No Price Plan",
            stripe_price_id="price_789",
            monthly_price=None,
            yearly_price=None,
        )

        cls.serializer = CheckoutSubscriptionSerializer
        cls.month = SubscriptionBillingCycleChoices.MONTH.value
        cls.year = SubscriptionBillingCycleChoices.YEAR.value

    def test_valid_monthly_plan(self):
        data = {"plan": self.monthly_plan.id, "billing_cycle": self.month}
        serializer = self.serializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_valid_yearly_plan(self):
        data = {"plan": self.yearly_plan.id, "billing_cycle": self.year}
        serializer = self.serializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_missing_plan(self):
        data = {"billing_cycle": self.month}
        serializer = self.serializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        self.assertIn("plan", context.exception.detail)

    def test_missing_billing_cycle(self):
        data = {"plan": self.monthly_plan.id}
        serializer = self.serializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        self.assertIn("billing_cycle", context.exception.detail)

    def test_invalid_billing_cycle(self):
        data = {"plan": self.monthly_plan.id, "billing_cycle": "weekly"}
        serializer = self.serializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        self.assertIn("billing_cycle", context.exception.detail)

    def test_plan_without_stripe_price_id(self):
        data = {"plan": self.plan_without_stripe_id.id, "billing_cycle": self.month}
        serializer = self.serializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        self.assertIn("plan", context.exception.detail)

    def test_plan_without_price(self):
        data = {"plan": self.plan_without_price.id, "billing_cycle": self.month}
        serializer = self.serializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        self.assertIn(
            "non_field_errors", context.exception.detail
        )  # Plan has no amount

    def test_case_insensitive_billing_cycle(self):
        data = {"plan": self.monthly_plan.id, "billing_cycle": "MONTH"}
        serializer = self.serializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        self.assertIn("billing_cycle", context.exception.detail)

    def test_numeric_billing_cycle(self):
        data = {"plan": self.monthly_plan.id, "billing_cycle": 123}
        serializer = self.serializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        self.assertIn("billing_cycle", context.exception.detail)

    def test_plan_object_instead_of_id(self):
        data = {"plan": self.monthly_plan, "billing_cycle": self.month}
        serializer = self.serializer(data=data)
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_extra_fields_in_data(self):
        data = {
            "plan": self.monthly_plan.id,
            "billing_cycle": self.month,
            "extra_field": "should be ignored",
        }
        serializer = self.serializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_empty_string_billing_cycle(self):
        data = {"plan": self.monthly_plan.id, "billing_cycle": ""}
        serializer = self.serializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        self.assertIn("billing_cycle", context.exception.detail)

    def test_null_billing_cycle(self):
        data = {"plan": self.monthly_plan.id, "billing_cycle": None}
        serializer = self.serializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        self.assertIn("billing_cycle", context.exception.detail)

    def test_invalid_plan_id(self):
        data = {"plan": 99999, "billing_cycle": self.month}
        serializer = self.serializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        self.assertIn("plan", context.exception.detail)

    @patch("apps.subscriptions.serializers.subscription.create_stripe_checkout_session")
    def test_get_checkout_session_url(self, mock_create_stripe_checkout_session):
        """Mock the Stripe API call to prevent real API interaction."""
        mock_create_stripe_checkout_session.return_value = (
            "https://stripe.com/checkout_test"
        )

        user = UserFactory(username="testuser1")
        profile = user.profile
        profile.stripe_customer_id = "1234"
        profile.save()

        serializer = self.serializer(
            data={"plan": self.monthly_plan.id, "billing_cycle": self.month}
        )
        serializer.is_valid()

        checkout_url = serializer.get_checkout_session_url(user)

        self.assertEqual(
            checkout_url["checkout_url"], "https://stripe.com/checkout_test"
        )
        mock_create_stripe_checkout_session.assert_called_once_with(
            self.monthly_plan, "1234"
        )
