"""
Enterprise Regression Test Suite for ValidationEngine v3.0

Covers:
- ResultCollector & _build_result DRY pattern
- AST whitelist eval security
- State immutability (original df never mutated)
- Rule registry execution
- Execution context (execution_id in results)
- Contract backward compatibility
- NaN domain safety
- Weighted severity scoring
- Zero mutation on contract object
"""
import unittest
import copy
import pandas as pd
import numpy as np
import os
from sentinel_gate.core.validation_engine import (
    ValidationEngine,
    ResultCollector,
    ValidationResult,
    _validate_expression,
)
from sentinel_gate.core.discovery_engine import DiscoveryEngine


class TestResultCollector(unittest.TestCase):
    """Tests for the decoupled ResultCollector."""

    def test_add_and_summary(self):
        collector = ResultCollector()
        collector.add(ValidationResult(
            rule_id="test_1", type="null_check", status="PASS",
            severity="LOW", mandatory=True, execution_id="abc123"
        ))
        collector.add(ValidationResult(
            rule_id="test_2", type="null_check", status="FAIL",
            severity="HIGH", mandatory=True, execution_id="abc123"
        ))
        summary = collector.summary()
        self.assertEqual(summary["total_checks"], 2)
        self.assertEqual(summary["pass"], 1)
        self.assertEqual(summary["fail"], 1)
        self.assertGreater(summary["score"], 0)

    def test_results_are_clean_dicts(self):
        collector = ResultCollector()
        collector.add(ValidationResult(
            rule_id="test", type="check", status="PASS",
            severity="LOW", mandatory=True, execution_id="x",
            column="col_a", metrics={"count": 0}
        ))
        results = collector.results
        self.assertIsInstance(results[0], dict)
        self.assertNotIn("columns", results[0])  # None fields omitted


class TestASTWhitelist(unittest.TestCase):
    """Tests for the AST expression validator."""

    def test_safe_expression_passes(self):
        _validate_expression("A + B == C")
        _validate_expression("A * B > 100")
        _validate_expression("A == B")

    def test_function_call_blocked(self):
        with self.assertRaises(ValueError) as ctx:
            _validate_expression("os.system('rm -rf /')")
        self.assertIn("Forbidden", str(ctx.exception))

    def test_import_blocked(self):
        with self.assertRaises(ValueError):
            _validate_expression("__import__('os')")

    def test_syntax_error_handled(self):
        with self.assertRaises(ValueError):
            _validate_expression("A ===== B")


class TestStateImmutability(unittest.TestCase):
    """Tests that original DataFrame is never mutated."""

    def test_filter_does_not_mutate_original(self):
        df = pd.DataFrame({"A": [1, 2, 3, 4, 5]})
        engine = ValidationEngine(df)
        original_len = len(df)

        # Simulate a filter by calling run_all with a filter
        engine.run_all({"filter": "A > 3", "null_checks": [{"column": "A", "max_percent": 100}]})

        # Original df must be unchanged
        self.assertEqual(len(df), original_len)
        # Engine's original must also be unchanged
        self.assertEqual(len(engine._original_df), original_len)

    def test_rerun_resets_state(self):
        df = pd.DataFrame({"A": [10, 20]})
        engine = ValidationEngine(df)
        contract = {"numeric_checks": [{"column": "A", "min": 15}]}

        out1 = engine.run_all(contract)
        out2 = engine.run_all(contract)
        self.assertEqual(out1["summary"]["total_checks"], out2["summary"]["total_checks"])


class TestContractImmutability(unittest.TestCase):
    """Tests that the original contract dict is never mutated by run_all."""

    def test_zero_mutation(self):
        df = pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})
        engine = ValidationEngine(df)
        original = {
            "primary_key": {"columns": ["id"], "mandatory": True},
            "uniqueness_checks": [{"columns": ["name"], "mandatory": True}]
        }
        snapshot = copy.deepcopy(original)
        engine.run_all(original)
        self.assertEqual(original, snapshot, "Contract was mutated!")


class TestNullChecks(unittest.TestCase):

    def test_basic_null_detection(self):
        df = pd.DataFrame({"A": [1, 2, None, 4]})
        engine = ValidationEngine(df)
        output = engine.run_all({"null_checks": [{"column": "A", "max_percent": 0}]})
        r = output["results"][0]
        self.assertEqual(r["status"], "FAIL")
        self.assertEqual(r["metrics"]["null_count"], 1)

    def test_execution_id_present(self):
        df = pd.DataFrame({"A": [1]})
        engine = ValidationEngine(df)
        output = engine.run_all({"null_checks": [{"column": "A", "max_percent": 100}]})
        self.assertIn("execution_id", output["results"][0])
        self.assertEqual(len(output["results"][0]["execution_id"]), 8)


class TestDomainChecks(unittest.TestCase):

    def test_nan_excluded_from_domain(self):
        df = pd.DataFrame({"status": ["ativo", "inativo", None, "ativo"]})
        engine = ValidationEngine(df)
        output = engine.run_all({"domain_checks": [{"column": "status", "allowed_values": ["ativo", "inativo"]}]})
        self.assertEqual(output["results"][0]["status"], "PASS")
        self.assertEqual(output["results"][0]["metrics"]["invalid_count"], 0)

    def test_forbidden_empty_list_no_crash(self):
        df = pd.DataFrame({"A": ["x", "y"]})
        engine = ValidationEngine(df)
        output = engine.run_all({"domain_checks": [{"column": "A", "forbidden_values": [], "allowed_values": ["x", "y"]}]})
        self.assertEqual(output["results"][0]["status"], "PASS")


class TestComparisonChecks(unittest.TestCase):

    def test_safe_comparison(self):
        df = pd.DataFrame({"A": [1, 2], "B": [1, 3]})
        engine = ValidationEngine(df)
        output = engine.run_all({"comparison_checks": [{"equation": "A == B"}]})
        self.assertEqual(output["results"][0]["metrics"]["invalid_count"], 1)

    def test_malicious_expression_blocked(self):
        df = pd.DataFrame({"A": [1]})
        engine = ValidationEngine(df)
        output = engine.run_all({"comparison_checks": [{"equation": "os.system('rm -rf /')"}]})
        self.assertEqual(output["results"][0]["status"], "FAIL")
        self.assertIn("Forbidden", output["results"][0].get("message", ""))


class TestBackwardCompatibility(unittest.TestCase):

    def test_old_duplicate_check_key(self):
        df = pd.DataFrame({"A": [1, 1, 2]})
        engine = ValidationEngine(df)
        output = engine.run_all({"duplicate_check": True})
        self.assertEqual(output["results"][0]["type"], "duplicate_row_check")

    def test_old_schema_key(self):
        df = pd.DataFrame({"A": [1, 2]})
        engine = ValidationEngine(df)
        output = engine.run_all({"schema": {"A": "int"}})
        self.assertEqual(output["results"][0]["type"], "schema_type_check")


class TestWeightedScore(unittest.TestCase):

    def test_score_is_weighted(self):
        df = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
        engine = ValidationEngine(df)
        output = engine.run_all({
            "null_checks": [
                {"column": "A", "max_percent": 100, "mandatory": True},
            ]
        })
        self.assertIsInstance(output["summary"]["score"], float)


class TestDiscoveryEngine(unittest.TestCase):

    def test_pk_detection_uses_ngroups(self):
        df = pd.DataFrame({"id": [1, 2, 3]})
        disco = DiscoveryEngine(df)
        res = disco.detect_primary_keys()
        self.assertEqual(res["status"], "PASS")


class TestRuleRegistry(unittest.TestCase):

    def test_all_check_types_routed(self):
        """Ensures the registry can handle a comprehensive contract."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["a", "b", "c"],
            "value": [10.0, 20.0, 30.0],
        })
        engine = ValidationEngine(df)
        contract = {
            "null_checks": [{"column": "id", "max_percent": 0}],
            "domain_checks": [{"column": "name", "allowed_values": ["a", "b", "c"]}],
            "numeric_checks": [{"column": "value", "min": 0}],
            "empty_string_checks": {"columns": ["name"]},
            "duplicate_row_check": True,
        }
        output = engine.run_all(contract)
        types = {r["type"] for r in output["results"]}
        self.assertIn("null_check", types)
        self.assertIn("domain_check", types)
        self.assertIn("numeric_check", types)
        self.assertIn("duplicate_row_check", types)


if __name__ == "__main__":
    unittest.main()
