from typing import List, Dict, Any
from data_profiler.utils.logger import logger

class ScoringEngine:
    """Calculates a Data Quality Score based on validation results."""

    @staticmethod
    def calculate_score(validation_results: List[Dict[str, Any]], drift_result: Dict[str, Any]) -> float:
        """
        Calculates score: (passed_checks / total_checks) * 100.
        Includes drift detection as one of the checks.
        """
        logger.info("Calculating Data Quality Score")
        total_checks = len(validation_results) + 1 # +1 for schema drift
        passed_checks = sum(1 for r in validation_results if r["status"] == "PASS")
        
        if drift_result["status"] == "PASS":
            passed_checks += 1
            
        if total_checks == 0:
            return 100.0
            
        score = (passed_checks / total_checks) * 100
        return round(score, 2)
