import os
from datetime import datetime
from typing import Dict, Any, Optional

from data_profiler.core.datasource import DataSource
from data_profiler.core.schema_inference import SchemaInference
from data_profiler.core.schema_validator import SchemaValidator
from data_profiler.core.validation_engine import ValidationEngine
from data_profiler.core.aggregation_engine import AggregationEngine
from data_profiler.core.scoring import ScoringEngine
from data_profiler.core.profiling import ProfilingEngine
from data_profiler.core.discovery_engine import DiscoveryEngine
from data_profiler.core.drift_detection import detect_drift
from data_profiler.core.report import ReportGenerator
from data_profiler.utils.logger import logger

def run_data_quality_workflow(config: Dict[str, Any], output_dir: str = ".") -> Dict[str, Any]:
    """Orchestrates the entire Data Quality workflow with nested output folders."""
    try:
        # Create unique run subfolder
        timestamp = datetime.now().strftime("%Y-%m-%d_%Hh%M")
        run_output_dir = os.path.join(output_dir, f"run_{timestamp}")
        os.makedirs(run_output_dir, exist_ok=True)
        
        # 1. LOAD DATA
        df = DataSource.load_data(config["source"])
        dataset_name = config["source"].get("table") or os.path.basename(config["source"].get("file", "unknown_dataset"))

        # 2. INFER TYPES
        inferred_schema = SchemaInference.infer_schema(df)

        # 3. SCHEMA VALIDATION
        drift_report = {"status": "NOT_RUN"}
        expected_schema = config.get("validations", {}).get("schema", {}).get("expected_columns")
        if expected_schema:
            drift_report = SchemaValidator.validate_schema(expected_schema, inferred_schema)

        # 4. DATA VALIDATIONS
        validations_config = config.get("validations", {})
        if not validations_config.get("null_checks") and not validations_config.get("group_by_checks") and not config.get("validations", {}).get("schema"):
            logger.info("No validations provided, adding default null checks for all columns")
            validations_config["null_checks"] = [{"column": col} for col in df.columns]

        val_engine = ValidationEngine(df.copy())
        validation_results = val_engine.run_all(validations_config)

        # 5. AGGREGATION CHECKS
        agg_config = validations_config.get("group_by_checks", [])
        agg_engine = AggregationEngine(df.copy())
        aggregation_results = agg_engine.run(agg_config, filter_query=validations_config.get("filter"))

        # 6. DISCOVERY ENGINE
        discovery_config = config.get("discovery", {})
        discovery_engine = DiscoveryEngine(df.copy())
        discovery_results = discovery_engine.run_all(discovery_config)

        # 7. DRIFT DETECTION (New)
        drift_results = {"status": "NOT_RUN"}
        if "reference" in config:
            try:
                logger.info("Loading reference dataset for drift detection")
                ref_df = DataSource.load_data(config["reference"])
                drift_results = detect_drift(ref_df, df, run_output_dir)
            except Exception as e:
                logger.error(f"Could not run drift detection: {e}")
                drift_results = {"status": "FAIL", "message": str(e)}

        # 8. SCORING
        scoring_config = config.get("scoring", {})
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
        profiling_config = config.get("profiling", {})
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

