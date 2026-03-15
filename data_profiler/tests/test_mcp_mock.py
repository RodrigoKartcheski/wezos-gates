import asyncio
import json
import os
from data_profiler.interfaces.mcp_server import load_and_validate, infer_dataset_schema

async def test_mcp_logic():
    print("Testing MCP Tools Logic...")
    
    # Test infer_schema tool
    csv_path = os.path.join("data_profiler", "tests", "sample_data", "sample_data.csv")
    schema_res = await infer_dataset_schema("csv", csv_path)
    schema = json.loads(schema_res)
    assert "id" in schema
    assert schema["id"]["inferred_type"] == "integer"
    print("✓ infer_dataset_schema passed")

    # Test load_and_validate tool
    rules_path = os.path.join("data_profiler", "tests", "sample_data", "rules.json")
    # For validation, we need to ensure the config refers to the correct file path
    # since main.py will run from the current CWD.
    with open(rules_path, 'r') as f:
        config = json.load(f)
    
    # Update file path to be relative to the mock run CWD
    config["source"]["file"] = csv_path
    
    val_res = await load_and_validate(json.dumps(config))
    report = json.loads(val_res)
    assert report["dataset"] == csv_path
    assert "data_quality_score" in report
    print(f"✓ load_and_validate passed - Score: {report['data_quality_score']}")

if __name__ == "__main__":
    asyncio.run(test_mcp_logic())
