from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.factories.subscription import SubscriptionFactory
from apps.subscriptions.serializers.subscription import SubscriptionSerializer

User = get_user_model()


class SubscriptionSerializerUnitTests(TestCase):
    def setUp(self):
        self.subscription = SubscriptionFactory(
            status=SubscriptionStatusChoices.ACTIVE.value
        )

    def test_serialized_fields(self):
        serializer = SubscriptionSerializer(instance=self.subscription)
        data = serializer.data
        self.assertIn("plan", data)
        self.assertIn("status", data)
        self.assertNotIn("id", data)
        self.assertNotIn("user", data)
        self.assertNotIn("stripe_subscription_id", data)
        self.assertNotIn("created_at", data)
        self.assertNotIn("updated_at", data)

    def test_nested_plan_serialization(self):
        serializer = SubscriptionSerializer(instance=self.subscription)
        data = serializer.data
        self.assertIsInstance(data["plan"], dict)
        self.assertEqual(data["plan"]["name"], self.subscription.plan.name)

    def test_invalid_data_plan_readonly(self):
        data = {
            "plan": {
                "name": self.subscription.plan.name,
                "monthly_price": str(self.subscription.plan.monthly_price)
            },
            "status": SubscriptionStatusChoices.ACTIVE.value
        }
        serializer = SubscriptionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
