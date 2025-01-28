import factory

from apps.subscriptions.models import Plan


class PlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Plan

    name = factory.Sequence(lambda n: f"Plan {n}")
    description = factory.Faker("sentence")
    monthly_price = factory.Faker("pydecimal", left_digits=2, right_digits=2, positive=True)
    yearly_price = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)
    is_active = True
