import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_data.py"
SPEC = importlib.util.spec_from_file_location("validate_data", SCRIPT)
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class ValidationTests(unittest.TestCase):
    def test_committed_source_registry_is_valid(self):
        self.assertEqual(validator.validate_sources(), [])

    def test_url_validation_requires_http_scheme_and_host(self):
        self.assertTrue(validator.valid_http_url("https://example.com/news"))
        self.assertFalse(validator.valid_http_url("javascript:alert(1)"))
        self.assertFalse(validator.valid_http_url("https:///missing-host"))


if __name__ == "__main__":
    unittest.main()
