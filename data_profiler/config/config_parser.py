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
        # Sections to auto-map from root keys
        mapping_rules = {
            "discovery": ["group_by", "dedupIncludeColumns", "dedupExcludeColumns", 
                          "date_analysis", "check_nulls", "check_outliers", 
                          "check_constants", "check_empty", "detect_keys"],
            "profiling": ["profiling_title", "title"]
        }

        # 1. Handle Simplified Source
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

        # Special case: 'filter' at root - maps to DISCOVERY only to keep others clean
        if "filter" in config:
            disco = config.setdefault("discovery", {})
            if "filter" not in disco:
                disco["filter"] = config.pop("filter")

        # 3. Handle Section Mappings (Discovery, Profiling, etc.)
        for section, keys in mapping_rules.items():
            if any(k in config for k in keys):
                logger.info(f"Auto-mapping keys to '{section}' section")
                sec_conf = config.setdefault(section, {})
                for k in keys:
                    if k in config and k not in sec_conf:
                        sec_conf[k] = config.pop(k)

        # Basic validation of config structure
        if "source" not in config:
            # If we STILL don't have a source, it's invalid unless CLI provides it
            # But the parser should ideally return what it has and let CLI handle merging
            pass

        return config
