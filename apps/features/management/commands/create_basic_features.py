from django.core.management.base import BaseCommand

from apps.features.choices.feature_code_choices import FeatureCodeChoices
from apps.features.models import Feature


class Command(BaseCommand):
    help = "Creates basic features with multilingual name/description and metadata if they don't exist"

    def handle(self, *args, **kwargs):
        basic_features = [
            {
                "code": FeatureCodeChoices.CLOUD_STORAGE,
                "name": {
                    "en": "Cloud Storage",
                    "es": "Almacenamiento en la Nube"
                },
                "description": {
                    "en": "Cloud file storage with upload support.",
                    "es": "Almacenamiento de archivos en la nube con soporte de subida."
                },
                "metadata": {
                    "max_storage_mb": 2048,
                    "max_file_size_mb": 200,
                    "file_types_allowed": ["pdf", "jpg", "png", "docx"]
                },
            },
            {
                "code": FeatureCodeChoices.FILE_PREVIEW,
                "name": {
                    "en": "File Preview",
                    "es": "Vista Previa de Archivos"
                },
                "description": {
                    "en": "Preview supported files in the browser.",
                    "es": "Vista previa de archivos compatibles en el navegador."
                },
                "metadata": {
                    "preview_file_types": ["pdf", "jpg", "png", "txt"]
                },
            },
            {
                "code": FeatureCodeChoices.FILE_SHARING,
                "name": {
                    "en": "File Sharing",
                    "es": "Compartir Archivos"
                },
                "description": {
                    "en": "Share files via secure link.",
                    "es": "Comparte archivos mediante un enlace seguro."
                },
                "metadata": {
                    "default_share_duration_minutes": 120
                },
            },
            {
                "code": FeatureCodeChoices.FOLDER_CREATION,
                "name": {
                    "en": "Folder Creation",
                    "es": "Creación de Carpetas"
                },
                "description": {
                    "en": "Create folders to organize uploaded files.",
                    "es": "Crea carpetas para organizar los archivos subidos."
                },
                "metadata": {},
            },
            {
                "code": FeatureCodeChoices.BASIC_SUPPORT,
                "name": {
                    "en": "Basic Support",
                    "es": "Soporte Básico"
                },
                "description": {
                    "en": "Basic email support for free-tier users.",
                    "es": "Soporte por correo electrónico básico para usuarios del plan gratuito."
                },
                "metadata": {
                    "support_email": "support@example.com"
                },
            },
        ]

        for feature_data in basic_features:
            feature, created = Feature.objects.get_or_create(
                code=feature_data["code"],
                defaults={
                    "name": feature_data["name"],
                    "description": feature_data["description"],
                    "metadata": feature_data["metadata"],
                    "is_active": True,
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created feature: {feature.code}"))
            else:
                self.stdout.write(self.style.WARNING(f"Feature already exists: {feature.code}"))
