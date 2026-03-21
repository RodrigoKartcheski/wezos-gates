from typing import List, Dict, Any
from data_profiler.utils.logger import logger

class ScoringEngine:
    """Calculates a Data Quality Score based on validation results."""

    DEFAULT_WEIGHTS = {
        "primary_key_check": 10,
        "uniqueness_check": 10,
        "duplicate_row_check": 5,
        "schema_type_check": 5,
        "date_check": 5,
        "schema_drift": 5, # Drift detection
        "domain_check": 3,
        "null_check": 2,
        "numeric_check": 2,
        "empty_string_check": 2,
        "volume_check": 1,
        "outlier_check": 1,
        "constant_check": 1
    }

    ANALYTICAL_CHECKS = {
        "primary_key_check", 
        "uniqueness_check", 
        "duplicate_row_check"
    }

    @classmethod
    def calculate_score(cls, validation_results: List[Dict[str, Any]], drift_result: Dict[str, Any], scoring_config: Dict[str, Any] = None) -> Dict[str, float]:
        """
        Calculates Technical, Analytical, and Final Data Quality Scores using a weighted system.
        """
        logger.info("Calculating Dual Weighted Data Quality Scores")
        
        scoring_config = scoring_config or {}
        custom_weights = scoring_config.get("weights", {})
        
        # Friendly name mapping
        name_map = {
            "primary_key": "primary_key_check",
            "uniqueness": "uniqueness_check",
            "schema": "schema_type_check",
            "date": "date_check",
            "domain": "domain_check",
            "null": "null_check",
            "numeric": "numeric_check",
            "empty": "empty_string_check",
            "empty_string": "empty_string_check",
            "volume": "volume_check",
            "outlier": "outlier_check",
            "constant": "constant_check"
        }
        
        mapped_custom_weights = {name_map.get(k, k): v for k, v in custom_weights.items()}
        
        # Merge weights
        weights = cls.DEFAULT_WEIGHTS.copy()
        weights.update(mapped_custom_weights)
        
        analytical_types = set(scoring_config.get("analytical_checks", cls.ANALYTICAL_CHECKS))
        
        scores = {
            "technical": {"passed_weight": 0.0, "total_weight": 0.0},
            "analytical": {"passed_weight": 0.0, "total_weight": 0.0}
        }
        
        all_checks = list(validation_results)
        if drift_result.get("status") in ["PASS", "FAIL"]:
            all_checks.append({"type": "schema_drift", "status": drift_result["status"]})
            
        for r in all_checks:
            r_type = r.get("type", "unknown")
            # Default weight to 1 if not explicitly mapped
            weight = weights.get(r_type, 1)
            
            # Map uniqueness_check specifically as it's the internal name 
            # if user typed 'uniqueness' in json, we might map it or just use 'uniqueness_check'
            
            category = "analytical" if r_type in analytical_types else "technical"
            
            scores[category]["total_weight"] += weight
            if r["status"] == "PASS":
                scores[category]["passed_weight"] += weight
                
        # Calculate percentages
        def calc_pct(cat):
            total = scores[cat]["total_weight"]
            passed = scores[cat]["passed_weight"]
            return round((passed / total) * 100, 2) if total > 0 else 100.0
            
        tech_score = calc_pct("technical")
        ana_score = calc_pct("analytical")
        
        total_weight = scores["technical"]["total_weight"] + scores["analytical"]["total_weight"]
        total_passed = scores["technical"]["passed_weight"] + scores["analytical"]["passed_weight"]
        
        final_score = round((total_passed / total_weight) * 100, 2) if total_weight > 0 else 100.0
        
        return {
            "technical_score": tech_score,
            "analytical_score": ana_score,
            "final_score": final_score
        }
