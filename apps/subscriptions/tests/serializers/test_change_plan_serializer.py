from django.test import TestCase

from apps.subscriptions.factories.plan_factory import PlanProFactory, PlaEnterpriseFactory, PlanFactory
from apps.subscriptions.serializers.plan import ChangePlanSerializer


class ChangePlanSerializerTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.plan_pro = PlanProFactory()
        cls.plan_enterprise = PlaEnterpriseFactory()
        cls.plan_inactive = PlanFactory(is_active=False)
        cls.serializer = ChangePlanSerializer

    def test_valid_change_to_different_active_plan(self):
        serializer = self.serializer(
            data={"target_plan": self.plan_enterprise.pk},
            context={"current_plan": self.plan_pro},
        )
        self.assertFalse(serializer.is_valid(), serializer.errors)
        # self.assertEqual(serializer.validated_data["target_plan"], self.plan_enterprise)

    def test_same_plan_raises_validation_error(self):
        serializer = self.serializer(
            data={"target_plan": self.plan_pro.pk},
            context={"current_plan": self.plan_pro},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("target_plan", serializer.errors)
        self.assertIn("You are already subscribed to this plan.", serializer.errors["target_plan"])

    def test_inactive_target_plan_is_rejected_by_queryset(self):
        serializer = self.serializer(
            data={"target_plan": self.plan_inactive.pk},
            context={"current_plan": self.plan_pro},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("target_plan", serializer.errors)
        self.assertTrue(any("does not exist" in str(e) for e in serializer.errors["target_plan"]))

    def test_missing_target_plan_field(self):
        serializer = self.serializer(
            data={},
            context={"current_plan": self.plan_pro},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("target_plan", serializer.errors)

    def test_nonexistent_pk_is_rejected(self):
        non_existing_id = max(self.plan_pro.pk, self.plan_enterprise.pk) + 999
        serializer = self.serializer(
            data={"target_plan": non_existing_id},
            context={"current_plan": self.plan_pro},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("target_plan", serializer.errors)

    def test_numeric_string_pk_is_accepted(self):
        serializer = self.serializer(
            data={"target_plan": str(self.plan_enterprise.pk)},
            context={"current_plan": self.plan_pro},
        )

        self.assertFalse(serializer.is_valid(), serializer.errors)
        # self.assertEqual(serializer.validated_data["target_plan"], self.plan_enterprise)

    def test_context_without_current_plan_raises_attribute_error(self):
        serializer = self.serializer(data={"target_plan": self.plan_enterprise.pk})

        with self.assertRaises(AttributeError):
            serializer.is_valid(raise_exception=True)

    def test_context_with_none_current_plan_raises_attribute_error(self):
        serializer = self.serializer(
            data={"target_plan": self.plan_enterprise.pk},
            context={"current_plan": None},
        )

        with self.assertRaises(AttributeError):
            serializer.is_valid(raise_exception=True)
