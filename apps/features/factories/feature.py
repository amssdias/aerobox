import factory

from apps.features.choices.feature_code_choices import FeatureCodeChoices
from apps.features.models import Feature


class FeatureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Feature

    code = FeatureCodeChoices.CLOUD_STORAGE.value
    name = {
        "en": "Cloud Storage",
        "es": "Almacenamiento en la Nube"
    }
    description = {
        "en": "Cloud file storage with upload support.",
        "es": "Almacenamiento de archivos en la nube con soporte de subida."
    }
    metadata = factory.LazyFunction(dict)
    is_active = True


class FeatureCloudStorageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Feature
        django_get_or_create = ("code",)

    code = FeatureCodeChoices.CLOUD_STORAGE.value
