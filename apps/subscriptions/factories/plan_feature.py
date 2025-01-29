import factory

from apps.subscriptions.models import PlanFeature


class PlanFeatureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PlanFeature

    metadata = {}
