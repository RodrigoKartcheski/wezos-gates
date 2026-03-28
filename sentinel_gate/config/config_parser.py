from typing import Dict, Any, Optional
from sentinel_gate.utils.json_loader import load_json
from sentinel_gate.utils.logger import logger
from sentinel_gate.config.models import SentinelConfig
from pydantic import ValidationError

class ConfigParser:
    """Parses and validates the SentinelGate configuration using Pydantic."""

    @staticmethod
    def parse(config_path: str) -> Dict[str, Any]:
        """Loads, auto-maps legacy keys, and validates the configuration."""
        logger.info(f"Parsing configuration from {config_path}")
        config = load_json(config_path)
        
        # 1. Legacy Auto-Mapping (Root keys to Sections)
        source_keys = ["file", "project", "dataset", "table", "sep", "encoding"]
        mapping_rules = {
            "discovery": ["group_by", "dedupIncludeColumns", "dedupExcludeColumns", 
                          "date_analysis", "check_nulls", "check_outliers", 
                          "check_constants", "check_empty", "detect_keys"],
            "profiling": ["profiling_title", "title"],
            "validations": ["null_checks", "primary_key", "uniqueness_checks", 
                            "domain_checks", "numeric_checks", "volume_checks", 
                            "constant_checks", "outlier_checks", "empty_string_checks", 
                            "duplicate_check", "schema", "date_checks", 
                            "comparison_checks", "lookup_checks", "unit_checks", 
                            "timestamp_checks"]
        }

        # Handle Simplified Source
        if any(k in config for k in source_keys) and "source" not in config:
            source_conf = {}
            if "file" in config:
                source_conf["type"] = "csv"
            elif all(k in config for k in ["project", "dataset", "table"]):
                source_conf["type"] = "bigquery"
            
            for k in source_keys:
                if k in config:
                    source_conf[k] = config.pop(k)
            config["source"] = source_conf

        # Map root filter to discovery
        if "filter" in config:
            disco = config.setdefault("discovery", {})
            if "filter" not in disco:
                disco["filter"] = config.pop("filter")

        # Map other sections
        for section, keys in mapping_rules.items():
            if any(k in config for k in keys):
                sec_conf = config.setdefault(section, {})
                for k in keys:
                    if k in config and k not in sec_conf:
                        sec_conf[k] = config.pop(k)

        # 2. Pydantic Validation
        try:
            validated_config = SentinelConfig.model_validate(config)
            # Return as dict for compatibility with the rest of the engine
            return validated_config.model_dump(exclude_unset=True, by_alias=True)
        except ValidationError as e:
            logger.error(f"Configuration validation failed for {config_path}")
            # Format Pydantic error into something readable
            error_msgs = []
            for err in e.errors():
                loc = " -> ".join([str(x) for x in err['loc']])
                msg = err['msg']
                error_msgs.append(f"[{loc}]: {msg}")
            
            error_details = "\n".join(error_msgs)
            raise ValueError(f"Invalid SentinelGate Configuration:\n{error_details}") from e
