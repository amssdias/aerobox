import time

from django.test import SimpleTestCase

from apps.cloud_storage.utils.hash_utils import generate_unique_hash


class GenerateUniqueHashTests(SimpleTestCase):
    def test_basic_functionality(self):
        filename = "example.txt"
        result = generate_unique_hash(filename)
        self.assertIsInstance(result, str)
        self.assertTrue(result.endswith(".txt"))

    def test_hash_uniqueness(self):
        filename = "example.txt"
        result1 = generate_unique_hash(filename)
        time.sleep(0.001)
        result2 = generate_unique_hash(filename)
        self.assertNotEqual(result1, result2)

    def test_extension_preservation(self):
        filename = "archive.tar.gz"
        result = generate_unique_hash(filename)
        self.assertTrue(result.endswith(".gz"))

    def test_filename_without_extension(self):
        filename = "no_extension"
        result = generate_unique_hash(filename)
        self.assertTrue(result.endswith(".no_extension"))

    def test_special_characters_in_filename(self):
        filename = "my file ☃ @home!.docx"
        result = generate_unique_hash(filename)
        self.assertTrue(result.endswith(".docx"))
        self.assertIsInstance(result, str)
