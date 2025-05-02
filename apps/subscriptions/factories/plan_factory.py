import factory

from apps.subscriptions.models import Plan


class PlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Plan

    name = factory.Sequence(lambda n: {"en": f"Plan {n}"})
    description = factory.Sequence(lambda n: {"en": f"Description {n}"})
    monthly_price = factory.Faker("pydecimal", left_digits=2, right_digits=2, positive=True)
    yearly_price = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)
    is_active = True
    stripe_price_id = factory.Faker("bothify", text="price_????####")
