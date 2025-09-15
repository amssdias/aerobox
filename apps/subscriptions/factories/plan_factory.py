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
    is_free = False


class PlanFreeFactory(PlanFactory):
    is_free = True
    monthly_price = 0
    yearly_price = 0
    stripe_price_id = None


class PlanProFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Plan
        django_get_or_create = ("name",)

    name = {
        "en": "Pro",
        "es": "Profesional",
    }


class PlaEnterpriseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Plan
        django_get_or_create = ("name",)

    name = {
        "en": "Enterprise",
        "es": "Empresas",
    }
