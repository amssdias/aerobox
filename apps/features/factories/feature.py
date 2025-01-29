import factory

from apps.features.choices.feature_code_choices import FeatureCodeChoices
from apps.features.models import Feature


class FeatureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Feature

    code = FeatureCodeChoices.CLOUD_STORAGE.value
    name = "Cloud storage"
    description = factory.Faker("sentence")
    metadata = {}
    is_active = True
