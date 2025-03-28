from datetime import timedelta

import factory
from django.utils.timezone import now

from apps.subscriptions.choices.subscription_choices import (
    SubscriptionBillingCycleChoices,
    SubscriptionStatusChoices,
)
from apps.subscriptions.factories.plan_factory import PlanFactory
from apps.subscriptions.models import Subscription
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
