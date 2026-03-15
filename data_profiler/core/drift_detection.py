from evidently import Report
from evidently.presets import DataDriftPreset
import pandas as pd
import os
from data_profiler.utils.logger import logger

def detect_drift(reference_df: pd.DataFrame, current_df: pd.DataFrame, output_path: str):
    """
    Detects data drift between reference and current datasets using Evidently.
    Generates a report_drift.html and returns a status summary.
    """
    logger.info("Running Data Drift Detection")

    # 1. Identify common columns
    common_columns = list(set(reference_df.columns).intersection(set(current_df.columns)))
    
    if not common_columns:
        logger.warning("No common columns found for drift detection. Skipping.")
        return {"status": "SKIPPED", "message": "No common columns found"}

    # 2. Filter datasets
    ref_filtered = reference_df[common_columns]
    cur_filtered = current_df[common_columns]

    # 3. Setup and Run Evidently Report
    report = Report(metrics=[
        DataDriftPreset(),
    ])

    try:
        snapshot = report.run(reference_data=ref_filtered, current_data=cur_filtered)
        
        # 4. Save HTML report
        report_file = os.path.join(output_path, "report_drift.html")
        snapshot.save_html(report_file)
        logger.info(f"Drift report saved to {report_file}")

        # 5. Extract summary (minimal breakdown)
        result_json = snapshot.dict()
        # Evidently structure for DataDriftPreset in .dict(): 
        # result_json['metrics'][0]
        drift_result = result_json['metrics'][0]
        
        summary = {
            "status": "SUCCESS",
            "share_of_drifted_columns": drift_result.get("share_of_drifted_columns", 0),
            "number_of_drifted_columns": drift_result.get("number_of_drifted_columns", 0),
            "dataset_drift": drift_result.get("dataset_drift", False)
        }
        
        return summary

    except Exception as e:
        logger.error(f"Drift detection failed: {e}", exc_info=True)
        return {"status": "FAIL", "message": str(e)}
