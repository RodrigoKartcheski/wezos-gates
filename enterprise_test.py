import sys
import os
import traceback
import pandas as pd

# Path injection
sys.path.insert(0, os.path.abspath("."))

if __name__ == "__main__":
    print("DEBUG: ENTERPRISE TEST START")
    from sentinel_gate.execution.orchestrator import run_data_quality_workflow
    
    test_csv = "enterprise_test.csv"
    df = pd.DataFrame({
        "id": range(200), 
        "val": range(200),
        "status": ["A", "B"] * 100,
        "email": ["test@example.com"] * 190 + [None] * 10
    })
    df.to_csv(test_csv, index=False)
    
    contract = {
        "source": {
            "type": "csv",
            "file": test_csv,
            "chunk_size": 40,
            "parallel_workers": 2
        },
        "quality_rules": {
            "null_checks": [{"column": "email", "max_percent": 10}],
            "numeric_checks": [{"column": "val", "min": 0}]
        },
        "discovery": {
            "detect_keys": True,
            "group_by": ["status"]
        }
    }
    
    try:
        result = run_data_quality_workflow(contract, output_dir="reports_enterprise")
        print(f"DEBUG: SUCCESS! Mode: {result['mode']}, Final Score: {result['scores']['final_score']}")
    except Exception:
        traceback.print_exc()
    finally:
        if os.path.exists(test_csv):
            os.remove(test_csv)
    print("DEBUG: ENTERPRISE TEST END")
