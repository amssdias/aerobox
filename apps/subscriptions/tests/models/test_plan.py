from unittest.mock import patch

from django.test import TestCase

from apps.features.choices.feature_code_choices import FeatureCodeChoices
from apps.features.factories.feature import FeatureCloudStorageFactory
from apps.subscriptions.factories.plan_factory import PlanProFactory
from apps.subscriptions.models import PlanFeature

BYTES_IN_MB = 1000 * 1000


class PlanModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.feature = FeatureCloudStorageFactory()
        cls.plan_pro = PlanProFactory()
        cls.cloud_storage_code = FeatureCodeChoices.CLOUD_STORAGE.value

    def setUp(self):
        self.plan_feature = PlanFeature.objects.get(plan=self.plan_pro, feature=self.feature)

    def test_effective_feature_metadata_merge_override(self):
        self.assertEqual(self.plan_feature.metadata["max_storage_mb"], 50000)
        self.assertEqual(self.plan_feature.metadata["max_file_size_mb"], 2000)

        self.plan_feature.metadata["max_storage_mb"] = 2222
        self.plan_feature.metadata["max_file_size_mb"] = 2200
        self.plan_feature.save()
        result = self.plan_pro.effective_feature_metadata(self.cloud_storage_code)

        self.assertEqual(result["max_storage_mb"], 2222)
        self.assertEqual(result["max_file_size_mb"], 2200)
        self.assertSetEqual(set(result.keys()), {"max_storage_mb", "max_file_size_mb", "blocked_file_types"})

    def test_effective_feature_metadata_only_override_present_with_empty_default(self):
        self.feature.metadata = {}
        self.feature.save(update_fields=["metadata"])
        max_storage_mb = self.plan_feature.metadata.get("max_storage_mb")
        max_file_size_mb = self.plan_feature.metadata.get("max_file_size_mb")

        result = self.plan_pro.effective_feature_metadata(self.cloud_storage_code)
        self.assertEqual(result["max_storage_mb"], max_storage_mb)
        self.assertEqual(result["max_file_size_mb"], max_file_size_mb)
        self.assertSetEqual(set(result.keys()), {"max_storage_mb", "max_file_size_mb", "blocked_file_types"})

    def test_effective_feature_metadata_no_feature(self):
        other_code = "NON_EXISTENT_FEATURE_CODE"
        result = self.plan_pro.effective_feature_metadata(other_code)
        self.assertEqual(result, {})

    def test_effective_feature_metadata_immutability(self):
        result = self.plan_pro.effective_feature_metadata(self.cloud_storage_code)
        result["flag"] = False
        result["retention_days"] = 99
        result["max_storage_mb"] = 777

        # Reload from DB and ensure originals intact
        self.feature.refresh_from_db()
        self.plan_feature.refresh_from_db()

        feature_max_storage_mb = self.feature.metadata["max_storage_mb"]
        feature_max_file_size_mb = self.feature.metadata["max_file_size_mb"]
        plan_feature_max_storage_mb = self.plan_feature.metadata["max_storage_mb"]
        plan_feature_max_file_size_mb = self.plan_feature.metadata["max_file_size_mb"]

        self.assertSetEqual(set(self.feature.metadata.keys()),
                            {"max_storage_mb", "max_file_size_mb", "blocked_file_types"})
        self.assertSetEqual(set(self.plan_feature.metadata.keys()),
                            {"max_storage_mb", "max_file_size_mb", "blocked_file_types"})

        self.assertEqual(self.feature.metadata["max_storage_mb"], feature_max_storage_mb)
        self.assertEqual(self.feature.metadata["max_file_size_mb"], feature_max_file_size_mb)
        self.assertEqual(self.plan_feature.metadata["max_storage_mb"], plan_feature_max_storage_mb)
        self.assertEqual(self.plan_feature.metadata["max_file_size_mb"], plan_feature_max_file_size_mb)

    def test_effective_feature_metadata_override_partial_update(self):
        feature_max_file_size_mb = self.feature.metadata["max_file_size_mb"]
        self.plan_feature.metadata = {"max_storage_mb": 1111}
        self.plan_feature.save(update_fields=["metadata"])

        result = self.plan_pro.effective_feature_metadata(self.cloud_storage_code)

        self.assertEqual(result["max_storage_mb"], 1111)
        self.assertEqual(result["max_file_size_mb"], feature_max_file_size_mb)

    def test_compute_storage_limit_bytes(self):
        plan_feature_max_storage_mb = self.plan_feature.metadata.get("max_storage_mb")
        max_storage_bytes = plan_feature_max_storage_mb * BYTES_IN_MB

        result = self.plan_pro._compute_storage_limit_bytes("max_storage_mb")

        self.assertEqual(result, max_storage_bytes)

    def test_compute_storage_limit_bytes_planfeature_override_wins_over_default(self):
        self.plan_feature.metadata["max_storage_mb"] = 1
        self.plan_feature.save(update_fields=["metadata"])

        result = self.plan_pro._compute_storage_limit_bytes("max_storage_mb")

        self.assertEqual(result, 1 * BYTES_IN_MB)

    def test_compute_storage_limit_bytes_missing_key_returns_none(self):
        self.feature.metadata = {}
        self.feature.save(update_fields=["metadata"])

        self.plan_feature.metadata = {}
        self.plan_feature.save(update_fields=["metadata"])

        result = self.plan_pro._compute_storage_limit_bytes("max_storage_mb")
        self.assertIsNone(result)

    def test_compute_storage_limit_bytes_wrong_key_returns_none(self):
        result = self.plan_pro._compute_storage_limit_bytes("max_storage_mbb")
        self.assertIsNone(result)

    def test_compute_storage_limit_bytes_non_numeric_value_returns_none(self):
        self.plan_feature.metadata["max_storage_mb"] = {"weird": "value"}
        self.plan_feature.save(update_fields=["metadata"])

        self.assertIsNone(self.plan_pro._compute_storage_limit_bytes("max_storage_mb"))

        self.plan_feature.metadata["max_storage_mb"] = "not-a-number"
        self.plan_feature.save(update_fields=["metadata"])

        self.assertIsNone(self.plan_pro._compute_storage_limit_bytes("max_storage_mb"))

    @patch("apps.subscriptions.models.plan.logger.error")
    def test_compute_storage_limit_bytes_negative_value(self, mock_logger):
        self.plan_feature.metadata["max_storage_mb"] = -2
        self.plan_feature.save(update_fields=["metadata"])

        result = self.plan_pro._compute_storage_limit_bytes("max_storage_mb")

        self.assertIsNone(result)
        mock_logger.assert_called_once()

    def test_compute_storage_limit_bytes_string_integer_value_is_parsed(self):
        self.plan_feature.metadata["max_storage_mb"] = "10"
        self.plan_feature.save(update_fields=["metadata"])

        self.assertEqual(self.plan_pro._compute_storage_limit_bytes("max_storage_mb"), 10 * BYTES_IN_MB)

    def test_compute_storage_limit_bytes_string_float_value(self):
        self.plan_feature.metadata["max_storage_mb"] = "5.5"
        self.plan_feature.save(update_fields=["metadata"])

        self.assertIsNone(self.plan_pro._compute_storage_limit_bytes("max_storage_mb"))

    def test_max_storage_bytes_returns_none_when_no_key_or_feature(self):
        self.feature.metadata = {}
        self.feature.save(update_fields=["metadata"])
        self.plan_feature.metadata = {}
        self.plan_feature.save(update_fields=["metadata"])

        self.assertIsNone(self.plan_pro.max_storage_bytes)

    def test_max_storage_bytes_returns_bytes_from_default_feature(self):
        self.plan_feature.metadata = {}
        self.plan_feature.save(update_fields=["metadata"])

        default_max_storage_mb = self.feature.metadata.get("max_storage_mb")

        self.assertEqual(self.plan_pro.max_storage_bytes, default_max_storage_mb * BYTES_IN_MB)

    def test_max_storage_bytes_planfeature_override_wins(self):
        plan_feature_max_storage_mb = self.plan_feature.metadata.get("max_storage_mb")

        self.assertEqual(self.plan_pro.max_storage_bytes, plan_feature_max_storage_mb * BYTES_IN_MB)

    @patch("apps.subscriptions.models.plan.logger.error")
    def test_max_storage_bytes_negative_value_current_behavior(self, mock_logger):
        self.plan_feature.metadata["max_storage_mb"] = -2
        self.plan_feature.save(update_fields=["metadata"])

        self.assertIsNone(self.plan_pro.max_storage_bytes)
        mock_logger.assert_called_once()

    def test_max_file_upload_size_bytes_returns_none_when_no_key_or_feature(self):
        self.feature.metadata = {}
        self.feature.save(update_fields=["metadata"])
        self.plan_feature.metadata = {}
        self.plan_feature.save(update_fields=["metadata"])

        self.assertIsNone(self.plan_pro.max_file_upload_size_bytes)

    def test_max_file_upload_size_bytes_returns_bytes_from_default_feature(self):
        self.plan_feature.metadata = {}
        self.plan_feature.save(update_fields=["metadata"])

        default_max_storage_mb = self.feature.metadata.get("max_file_size_mb")

        self.assertEqual(self.plan_pro.max_file_upload_size_bytes, default_max_storage_mb * BYTES_IN_MB)

    def test_max_file_upload_size_bytes_planfeature_override_wins(self):
        plan_feature_max_storage_mb = self.plan_feature.metadata.get("max_file_size_mb")

        self.assertEqual(self.plan_pro.max_file_upload_size_bytes, plan_feature_max_storage_mb * BYTES_IN_MB)
