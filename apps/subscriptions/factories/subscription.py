from datetime import timedelta

import factory
from django.utils.timezone import now

from apps.subscriptions.choices.subscription_choices import (
    SubscriptionBillingCycleChoices,
    SubscriptionStatusChoices,
)
from apps.subscriptions.factories.plan_factory import PlanFactory
from apps.subscriptions.models import Subscription, Plan
from apps.users.factories.user_factory import UserFactory


class SubscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Subscription

    user = factory.SubFactory(UserFactory)
    plan = factory.SubFactory(PlanFactory)
    stripe_subscription_id = factory.Faker("uuid4")
    billing_cycle = SubscriptionBillingCycleChoices.MONTH.value
    start_date = factory.LazyFunction(lambda: now().date())
    end_date = factory.LazyAttribute(lambda obj: obj.start_date + timedelta(days=31))
    status = SubscriptionStatusChoices.ACTIVE.value
    is_recurring = True


class SubscriptionFreePlanFactory(SubscriptionFactory):
    plan = factory.LazyFunction(lambda: Plan.objects.get_or_create(
        is_free=True,
        defaults={
            "name": {"en": "Free Plan"},
            "description": {"en": "Free plan description"},
            "monthly_price": 0,
            "yearly_price": 0,
            "stripe_price_id": None,
            "is_active": True,
        }
    )[0])
    stripe_subscription_id = None


class SubscriptionProPlanFactory(SubscriptionFactory):
    plan = factory.LazyFunction(lambda: Plan.objects.get_or_create(
        is_free=False,
        name__en="Pro",
        defaults={
            "name": {"en": "Pro Plan"},
            "description": {"en": "Pro plan description"},
            "monthly_price": 4.99,
            "yearly_price": 0,
            "stripe_price_id": None,
            "is_active": True,
        }
    )[0])
    stripe_subscription_id = None


class SubscriptionEnterprisePlanFactory(SubscriptionFactory):
    plan = factory.LazyFunction(lambda: Plan.objects.get_or_create(
        is_free=False,
        name__en="Enterprise",
        defaults={
            "name": {"en": "Enterprise"},
            "description": {"en": "Enterprise plan description"},
            "monthly_price": 99.99,
            "yearly_price": 0,
            "stripe_price_id": None,
            "is_active": True,
        }
    )[0])
    stripe_subscription_id = None
