from typing import Dict, Any, List, Optional
from sentinel_gate.utils.logger import logger

class SchemaValidator:
    """Detects schema drift by comparing expected vs actual inferred schema."""

    @staticmethod
    def validate_schema(expected_schema: Dict[str, str], actual_schema: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """
        Compares expected_schema (col: type) with actual_schema (col: {source_type, inferred_type}).
        Returns a drift report.
        """
        logger.info("Comparing schemas for drift detection")
        drift = {
            "missing_columns": [],
            "extra_columns": [],
            "type_mismatches": [],
            "status": "PASS"
        }

        actual_cols = set(actual_schema.keys())
        expected_cols = set(expected_schema.keys())

        # 1. Missing columns
        drift["missing_columns"] = list(expected_cols - actual_cols)

        # 2. Extra columns
        drift["extra_columns"] = list(actual_cols - expected_cols)

        # 3. Type mismatches
        for col in expected_cols.intersection(actual_cols):
            expected_type = expected_schema[col]
            actual_type = actual_schema[col]["inferred_type"]
            if expected_type != actual_type:
                drift["type_mismatches"].append({
                    "column": col,
                    "expected": expected_type,
                    "actual": actual_type
                })

        if drift["missing_columns"] or drift["type_mismatches"]:
            drift["status"] = "FAIL"
        
        return drift
