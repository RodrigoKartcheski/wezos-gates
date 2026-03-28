from typing import Dict, Any

# Templates for common validation rules to help users and IA
RULE_TEMPLATES = {
    "null_check": {
        "column": "column_name",
        "max_percent": 0
    },
    "primary_key": ["id_column"],
    "domain_check": {
        "column": "column_name",
        "allowed_values": ["VAL1", "VAL2"]
    },
    "numeric_check": {
        "column": "column_name",
        "min": 0,
        "max": 100
    },
    "volume_check": {
        "min_rows": 1,
        "max_rows": 1000000
    },
    "comparison_check": {
        "equation": "column_a * column_b == column_c",
        "mandatory": True
    },
    "lookup_check": {
        "column": "id_column",
        "reference_source": {"type": "csv", "file": "path/to/reference.csv"},
        "reference_column": "id",
        "mandatory": True
    },
    "unit_check": {
        "column": "weight_kg",
        "unit": "kg",
        "min_magnitude": 0,
        "max_magnitude": 1000
    },
    "timestamp_check": {
        "column": "created_at",
        "format_type": "iso_timezone"
    }
}
