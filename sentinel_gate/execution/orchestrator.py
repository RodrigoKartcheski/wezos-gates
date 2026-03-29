import os
import concurrent.futures
from datetime import datetime
from typing import Dict, Any, Optional, List

# (Removed early-binding imports to fix Windows hang)

# (Removed early-binding worker import to fix Windows hang)

def run_data_quality_workflow(contract: Dict[str, Any], output_dir: str = "reports") -> Dict[str, Any]:
    """Orchestrates the entire Data Quality workflow (supports Parallel & Chunked modes)."""
    from sentinel_gate.execution.workers import validate_chunk_task
    from sentinel_gate.execution.datasource import DataSource
    from sentinel_gate.contracts.inference import SchemaInference
    from sentinel_gate.contracts.validator import SchemaValidator
    from sentinel_gate.core.validation import ValidationEngine, ResultCollector
    from sentinel_gate.core.scoring import ScoringEngine
    from sentinel_gate.discovery.profiling import ProfilingEngine
    from sentinel_gate.discovery.engine import DiscoveryEngine
    from sentinel_gate.core.drift import detect_drift
    from sentinel_gate.core.report import ReportGenerator
    from sentinel_gate.utils.logger import logger
    try:
        # 0. ENSURE BASE REPORTS DIR
        if not os.path.isabs(output_dir) and not output_dir.startswith("reports") and output_dir != ".":
             output_dir = os.path.join("reports", output_dir)
             
        os.makedirs(output_dir, exist_ok=True)

        # Create unique run subfolder
        timestamp = datetime.now().strftime("%Y-%m-%d_%Hh%M")
        run_output_dir = os.path.join(output_dir, f"run_{timestamp}")
        os.makedirs(run_output_dir, exist_ok=True)
        
        # 1. LOAD DATA CONFIG
        source_config = contract["source"]
        data_iterator = DataSource.load_data(source_config)
        chunk_size = source_config.get("chunk_size")
        parallel_workers = source_config.get("parallel_workers", 1)
        dataset_name = source_config.get("table") or os.path.basename(source_config.get("file", "unknown_dataset"))

        # Initialize global state
        global_val_collector = ResultCollector()
        global_disco_results = None
        inferred_schema = None
        df_for_profiling = None
        
        # Pydantic-aware mapping (SentinelConfig uses 'validations')
        quality_rules = contract.get("validations", {})
        discovery_contract = contract.get("discovery")

        # 2. PROCESS DATA (PARALLEL vs SEQUENTIAL)
        if chunk_size and parallel_workers > 1:
            logger.info(f"Executing workflow in PARALLEL mode with {parallel_workers} workers")
            # Using ProcessPoolExecutor with late-binding imports
            with concurrent.futures.ProcessPoolExecutor(max_workers=parallel_workers) as executor:
                futures = {}
                for i, chunk_df in enumerate(data_iterator):
                    if inferred_schema is None:
                        inferred_schema = SchemaInference.infer_schema(chunk_df)
                        df_for_profiling = chunk_df.copy() # First chunk as sample
                    
                    # Submit to pool
                    fut = executor.submit(validate_chunk_task, chunk_df, quality_rules, discovery_contract)
                    futures[fut] = i
                
                # Collect results
                for future in concurrent.futures.as_completed(futures):
                    chunk_id = futures[future]
                    try:
                        worker_res = future.result()
                        global_val_collector.merge_partial_results(worker_res["val_results"])
                        
                        if worker_res["disco_results"]:
                            if global_disco_results is None:
                                global_disco_results = worker_res["disco_results"]
                            else:
                                for key, val in worker_res["disco_results"].items():
                                    if key not in global_disco_results:
                                        global_disco_results[key] = val
                                    elif isinstance(val, dict):
                                        global_disco_results[key].update(val)
                                    elif isinstance(val, list):
                                        global_disco_results[key].extend(val)
                    except Exception as e:
                        logger.error(f"Worker failed for chunk {chunk_id}: {e}")
                        raise
            
            validation_results = global_val_collector.results
            discovery_results = global_disco_results or {"column_stats": {}}
            
        elif chunk_size:
            # SEQUENTIAL CHUNKING
            logger.info("Executing workflow in SEQUENTIAL CHUNKED mode")
            for i, chunk_df in enumerate(data_iterator):
                if inferred_schema is None:
                    inferred_schema = SchemaInference.infer_schema(chunk_df)
                    df_for_profiling = chunk_df.copy()
                
                chunk_val_engine = ValidationEngine(chunk_df)
                chunk_val_output = chunk_val_engine.run_all(quality_rules)
                global_val_collector.merge_partial_results(chunk_val_output["results"])
                
                if discovery_contract:
                    disco_engine = DiscoveryEngine(chunk_df)
                    partial_disco = disco_engine.run_all(discovery_contract)
                    if global_disco_results is None:
                        global_disco_results = partial_disco
                    else:
                        for key, val in partial_disco.items():
                            if key not in global_disco_results:
                                global_disco_results[key] = val
                            elif isinstance(val, dict):
                                global_disco_results[key].update(val)
                            elif isinstance(val, list):
                                global_disco_results[key].extend(val)

            validation_results = global_val_collector.results
            discovery_results = global_disco_results or {"column_stats": {}}
        else:
            # SINGLE DF MODE
            df = data_iterator
            inferred_schema = SchemaInference.infer_schema(df)
            val_engine = ValidationEngine(df.copy())
            validation_output = val_engine.run_all(quality_rules)
            validation_results = validation_output["results"]
            discovery_results = DiscoveryEngine(df.copy()).run_all(discovery_contract) if discovery_contract else {"column_stats": {}}
            df_for_profiling = df

        # 3. SCHEMA VALIDATION & DRIFT
        drift_report = {"status": "NOT_RUN"}
        # SentinelConfig maps 'schema' to 'schema_type_checks' and it is inside 'validations'
        expected_schema = quality_rules.get("schema_type_checks")
        if expected_schema:
            drift_report = SchemaValidator.validate_schema(expected_schema, inferred_schema)

        # 4. DRIFT DETECTION
        drift_results = {"status": "NOT_RUN"}
        if contract.get("reference"): # Use .get() to avoid errors if key exists but is None
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
