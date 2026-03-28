import unittest
import os
import json
from sentinel_gate.config.config_parser import ConfigParser

class TestConfigValidation(unittest.TestCase):
    def setUp(self):
        self.temp_config = "temp_config.json"

    def tearDown(self):
        if os.path.exists(self.temp_config):
            os.remove(self.temp_config)

    def write_config(self, config_dict):
        with open(self.temp_config, "w") as f:
            json.dump(config_dict, f)

    def test_valid_csv_config(self):
        config = {
            "source": {
                "type": "csv",
                "file": "dummy.csv"
            },
            "validations": {
                "null_checks": [{"column": "col1", "max_percent": 0.05}]
            }
        }
        self.write_config(config)
        parsed = ConfigParser.parse(self.temp_config)
        self.assertEqual(parsed["source"]["type"], "csv")

    def test_valid_yaml_config(self):
        yaml_config = "temp_config.yaml"
        content = """
source:
  type: csv
  file: mock.csv
validations:
  duplicate_check: true
"""
        with open(yaml_config, "w") as f:
            f.write(content)
        
        try:
            parsed = ConfigParser.parse(yaml_config)
            self.assertEqual(parsed["source"]["type"], "csv")
            self.assertTrue(parsed["validations"]["duplicate_check"])
        finally:
            if os.path.exists(yaml_config):
                os.remove(yaml_config)

    def test_invalid_source_type(self):
        config = {
            "source": {
                "type": "invalid_type",
                "file": "dummy.csv"
            }
        }
        self.write_config(config)
        with self.assertRaises(ValueError) as cm:
            ConfigParser.parse(self.temp_config)
        self.assertIn("source -> type", str(cm.exception))

    def test_missing_csv_file(self):
        config = {
            "source": {
                "type": "csv"
            }
        }
        self.write_config(config)
        with self.assertRaises(ValueError) as cm:
            ConfigParser.parse(self.temp_config)
        # Pydantic V2 model_validator (after) points to the model 'source'
        self.assertIn("[source]: Value error, Field 'file' is required", str(cm.exception))

    def test_legacy_auto_mapping(self):
        # Test if root keys are still mapped to sections correctly
        config = {
            "file": "legacy.csv",
            "null_checks": [{"column": "col1"}],
            "group_by": ["cat1"]
        }
        self.write_config(config)
        parsed = ConfigParser.parse(self.temp_config)
        self.assertEqual(parsed["source"]["type"], "csv")
        self.assertEqual(parsed["source"]["file"], "legacy.csv")
        self.assertIn("null_checks", parsed["validations"])
        self.assertIn("group_by", parsed["discovery"])

    def test_invalid_rule_type(self):
        config = {
            "source": {"type": "csv", "file": "d.csv"},
            "validations": {
                "null_checks": [{"column": 123}] # Column should be string
            }
        }
        self.write_config(config)
        with self.assertRaises(ValueError) as cm:
            ConfigParser.parse(self.temp_config)
        self.assertIn("null_checks -> 0 -> column", str(cm.exception))

if __name__ == "__main__":
    unittest.main()
