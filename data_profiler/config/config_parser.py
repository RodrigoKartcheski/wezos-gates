from typing import Dict, Any, Optional
from data_profiler.utils.json_loader import load_json
from data_profiler.utils.logger import logger

class ConfigParser:
    """Parses the validation configuration JSON."""

    @staticmethod
    def parse(config_path: str) -> Dict[str, Any]:
        """Loads and validates the configuration JSON with simplified mapping."""
        logger.info(f"Parsing configuration from {config_path}")
        config = load_json(config_path)
        
        # Keys that should go into 'source'
        source_keys = ["file", "project", "dataset", "table", "sep", "encoding"]
        # Keys that should go into 'discovery'
        discovery_keys = [
            "group_by", "dedupIncludeColumns", "dedupExcludeColumns", 
            "date_analysis", "check_nulls", "check_outliers", 
            "check_constants", "check_empty", "detect_keys"
        ]

        # 1. Handle Simplified Source (file at root or BQ fields at root)
        if any(k in config for k in source_keys) and "source" not in config:
            logger.info("Auto-mapping root keys to 'source'")
            source_conf = {}
            if "file" in config:
                source_conf["type"] = "csv"
            elif all(k in config for k in ["project", "dataset", "table"]):
                source_conf["type"] = "bigquery"
            
            for k in source_keys:
                if k in config:
                    source_conf[k] = config.pop(k)
            config["source"] = source_conf

        # 2. Handle Simplified Discovery (discovery-specific keys at root)
        if any(k in config for k in discovery_keys):
            logger.info("Auto-mapping discovery keys to 'discovery' section")
            disco = config.setdefault("discovery", {})
            if "group_by" not in disco:
                disco["group_by"] = config.pop("group_by")

        # Basic validation of config structure
        if "source" not in config:
            # If we STILL don't have a source, it's invalid unless CLI provides it
            # But the parser should ideally return what it has and let CLI handle merging
            pass

        return config
