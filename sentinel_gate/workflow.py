import os
from datetime import datetime
from typing import Dict, Any, Optional

from sentinel_gate.core.datasource import DataSource
from sentinel_gate.core.schema_inference import SchemaInference
from sentinel_gate.core.schema_validator import SchemaValidator
from sentinel_gate.core.validation_engine import ValidationEngine
from sentinel_gate.core.aggregation_engine import AggregationEngine
from sentinel_gate.core.scoring import ScoringEngine
from sentinel_gate.core.profiling import ProfilingEngine
from sentinel_gate.core.discovery_engine import DiscoveryEngine
from sentinel_gate.core.drift_detection import detect_drift
from sentinel_gate.core.report import ReportGenerator
from sentinel_gate.utils.logger import logger

def run_data_quality_workflow(contract: Dict[str, Any], output_dir: str = "reports") -> Dict[str, Any]:
    """Orchestrates the entire Data Quality workflow with nested output folders."""
    try:
        # 0. ENSURE BASE REPORTS DIR
        # If output_dir is a relative path that doesn't start with 'reports', prepend it
        if not os.path.isabs(output_dir) and not output_dir.startswith("reports") and output_dir != ".":
             output_dir = os.path.join("reports", output_dir)
             
        os.makedirs(output_dir, exist_ok=True)

        # Create unique run subfolder
        timestamp = datetime.now().strftime("%Y-%m-%d_%Hh%M")
        run_output_dir = os.path.join(output_dir, f"run_{timestamp}")
        os.makedirs(run_output_dir, exist_ok=True)
        
        # 1. LOAD DATA
        df = DataSource.load_data(contract["source"])
        dataset_name = contract["source"].get("table") or os.path.basename(contract["source"].get("file", "unknown_dataset"))

        # 2. INFER TYPES
        inferred_schema = SchemaInference.infer_schema(df)

        # 3. SCHEMA VALIDATION
        drift_report = {"status": "NOT_RUN"}
        expected_schema = contract.get("quality_rules", {}).get("schema", {}).get("expected_columns")
        if expected_schema:
            drift_report = SchemaValidator.validate_schema(expected_schema, inferred_schema)

        # 4. DATA QUALITY RULES (CONTRACT)
        quality_rules = contract.get("quality_rules", {})
        if not quality_rules.get("null_checks") and not quality_rules.get("group_by_checks") and not contract.get("quality_rules", {}).get("schema"):
            logger.info("No quality rules provided, adding default null checks for all columns")
            quality_rules["null_checks"] = [{"column": col} for col in df.columns]

        val_engine = ValidationEngine(df.copy())
        validation_output = val_engine.run_all(quality_rules)
        validation_results = validation_output["results"]
        technical_score = validation_output["summary"]["score"]

        # 5. AGGREGATION CHECKS
        agg_config = quality_rules.get("group_by_checks", [])
        agg_engine = AggregationEngine(df.copy())
        aggregation_results = agg_engine.run(agg_config, filter_query=quality_rules.get("filter"))

        # 6. DISCOVERY ENGINE
        discovery_contract = contract.get("discovery", {})
        discovery_engine = DiscoveryEngine(df.copy())
        discovery_results = discovery_engine.run_all(discovery_contract)

        # 7. DRIFT DETECTION (New)
        drift_results = {"status": "NOT_RUN"}
        if "reference" in contract:
            try:
                logger.info("Loading reference dataset for drift detection")
                ref_df = DataSource.load_data(contract["reference"])
                drift_results = detect_drift(ref_df, df, run_output_dir)
            except Exception as e:
                logger.error(f"Could not run drift detection: {e}")
                drift_results = {"status": "FAIL", "message": str(e)}

        # 8. SCORING
        scoring_config = contract.get("scoring", {})
        scores = ScoringEngine.calculate_score(validation_results, drift_report, scoring_config)

        # 10. GENERATE HTML REPORTS (Target run_output_dir)
        schema_html = os.path.join(run_output_dir, "report_schema.html")
        ReportGenerator.generate_schema_html(dataset_name, drift_report, inferred_schema, schema_html)

        validations_html = os.path.join(run_output_dir, "report_validations.html")
        ReportGenerator.generate_validations_html(dataset_name, scores, validation_results, aggregation_results, validations_html)

        discovery_html = os.path.join(run_output_dir, "report_discovery.html")
        ReportGenerator.generate_discovery_html(dataset_name, discovery_results, discovery_html)

        logger.info(f"Profiling: Passing df with {len(df)} rows")
        profile_html = os.path.join(run_output_dir, "report_profiling.html")
        profiling_config = contract.get("profiling", {})
        # Note: ProfilingEngine.generate_report already uses apply_sql_filter which clones
        ProfilingEngine.generate_report(df.copy(), output_file=profile_html, title=f"Profile: {dataset_name}", filter_query=profiling_config.get("filter"))

        dashboard_html = os.path.join(run_output_dir, "dashboard.html")
        ReportGenerator.generate_dashboard_html(dataset_name, schema_html, validations_html, profile_html, discovery_html, dashboard_html)
        
        # Also generate to top-level for convenience
        top_level_dashboard = os.path.join(output_dir, "dashboard.html")
        ReportGenerator.generate_dashboard_html(dataset_name, schema_html, validations_html, profile_html, discovery_html, top_level_dashboard)
        
        logger.info(f"Workflow completed. Reports in: {run_output_dir}")
        logger.info(f"Latest Dashboard: {top_level_dashboard}")
        return {
            "dataset": dataset_name,
            "scores": scores,
            "reports_dir": run_output_dir
        }

    except Exception as e:
        logger.error(f"Workflow failed: {e}", exc_info=True)
        raise

