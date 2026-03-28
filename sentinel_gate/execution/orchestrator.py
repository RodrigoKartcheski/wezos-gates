import os
from datetime import datetime
from typing import Dict, Any, Optional

from sentinel_gate.execution.datasource import DataSource
from sentinel_gate.contracts.inference import SchemaInference
from sentinel_gate.contracts.validator import SchemaValidator
from sentinel_gate.core.validation import ValidationEngine
from sentinel_gate.core.aggregation import AggregationEngine
from sentinel_gate.core.scoring import ScoringEngine
from sentinel_gate.discovery.profiling import ProfilingEngine
from sentinel_gate.discovery.engine import DiscoveryEngine
from sentinel_gate.core.drift import detect_drift
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
        
        # 1. LOAD DATA (Support Chunking)
        data_iterator = DataSource.load_data(contract["source"])
        chunk_size = contract["source"].get("chunk_size")
        dataset_name = contract["source"].get("table") or os.path.basename(contract["source"].get("file", "unknown_dataset"))

        # Initialize global state for chunked runs
        global_val_collector = ResultCollector()
        global_disco_results = None
        inferred_schema = None
        all_dfs = [] # only used if not chunking
        
        # 2. PROCESS DATA (Loop or Single Load)
        if chunk_size:
            logger.info("Executing workflow in CHUNKED mode")
            for i, chunk_df in enumerate(data_iterator):
                logger.info(f"Processing chunk {i+1}")
                if inferred_schema is None:
                    inferred_schema = SchemaInference.infer_schema(chunk_df)
                
                # Validation
                quality_rules = contract.get("quality_rules", {})
                chunk_val_engine = ValidationEngine(chunk_df)
                chunk_val_output = chunk_val_engine.run_all(quality_rules)
                global_val_collector.merge_partial_results(chunk_val_output["results"])
                
                # Discovery (Incremental)
                discovery_contract = contract.get("discovery", {})
                if discovery_contract:
                    disco_engine = DiscoveryEngine(chunk_df)
                    partial_disco = disco_engine.run_all(discovery_contract)
                    if global_disco_results is None:
                        global_disco_results = partial_disco
                    else:
                        # Simple merge for discovery (Future: full DiscoveryEngine.merge)
                        global_disco_results["column_stats"] = {**global_disco_results["column_stats"], **partial_disco["column_stats"]}
                
                # For profiling, we take the first chunk as a representative sample
                if i == 0:
                    sample_df_for_profiling = chunk_df.copy()

            df_for_profiling = sample_df_for_profiling
            validation_results = global_val_collector.results
            discovery_results = global_disco_results or {"column_stats": {}}
            # Volume check needs the total row count from metrics
            total_rows = sum(r["metrics"].get("row_count", 0) for r in validation_results if r["type"] == "volume_check")
        else:
            # LEGACY / Standard Mode
            df = data_iterator
            inferred_schema = SchemaInference.infer_schema(df)
            
            quality_rules = contract.get("quality_rules", {})
            val_engine = ValidationEngine(df.copy())
            validation_output = val_engine.run_all(quality_rules)
            validation_results = validation_output["results"]
            
            discovery_engine = DiscoveryEngine(df.copy())
            discovery_results = discovery_engine.run_all(contract.get("discovery", {}))
            df_for_profiling = df

        # 3. SCHEMA VALIDATION & DRIFT
        drift_report = {"status": "NOT_RUN"}
        expected_schema = contract.get("quality_rules", {}).get("schema", {}).get("expected_columns")
        if expected_schema:
            drift_report = SchemaValidator.validate_schema(expected_schema, inferred_schema)

        # 4. DRIFT DETECTION
        drift_results = {"status": "NOT_RUN"}
        if "reference" in contract:
            try:
                ref_df = DataSource.load_data(contract["reference"])
                drift_results = detect_drift(ref_df, df_for_profiling, run_output_dir)
            except Exception as e:
                logger.error(f"Could not run drift detection: {e}")

        # 5. SCORING
        scoring_config = contract.get("scoring", {})
        scores = ScoringEngine.calculate_score(validation_results, drift_report, scoring_config)

        # 6. REPORTS
        schema_html = os.path.join(run_output_dir, "report_schema.html")
        ReportGenerator.generate_schema_html(dataset_name, drift_report, inferred_schema, schema_html)

        validations_html = os.path.join(run_output_dir, "report_validations.html")
        ReportGenerator.generate_validations_html(dataset_name, scores, validation_results, [], validations_html)

        discovery_html = os.path.join(run_output_dir, "report_discovery.html")
        ReportGenerator.generate_discovery_html(dataset_name, discovery_results, discovery_html)

        profile_html = os.path.join(run_output_dir, "report_profiling.html")
        ProfilingEngine.generate_report(df_for_profiling, output_file=profile_html, title=f"Profile (Sample): {dataset_name}")

        dashboard_html = os.path.join(run_output_dir, "dashboard.html")
        ReportGenerator.generate_dashboard_html(dataset_name, schema_html, validations_html, profile_html, discovery_html, dashboard_html)
        
        # Latest copy
        top_level_dashboard = os.path.join(output_dir, "dashboard.html")
        ReportGenerator.generate_dashboard_html(dataset_name, schema_html, validations_html, profile_html, discovery_html, top_level_dashboard)
        
        return {
            "dataset": dataset_name,
            "scores": scores,
            "reports_dir": run_output_dir,
            "mode": "chunked" if chunk_size else "batch"
        }

    except Exception as e:
        logger.error(f"Workflow failed: {e}", exc_info=True)
        raise

