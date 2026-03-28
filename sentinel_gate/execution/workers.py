import logging
from typing import Dict, Any, Optional
from sentinel_gate.core.validation import ValidationEngine
from sentinel_gate.discovery.engine import DiscoveryEngine

def validate_chunk_task(chunk_df: Any, quality_rules: Dict[str, Any], discovery_contract: Optional[Dict[str, Any]] = None):
    # Disable logging in worker to prevent deadlocks on Windows handles
    logging.getLogger("sentinel_gate").setLevel(logging.ERROR)
    """
    Standardized worker task for parallel chunk validation.
    Designed to be picklable and isolated from the main orchestrator.
    """
    # 1. Validation
    val_engine = ValidationEngine(chunk_df)
    val_output = val_engine.run_all(quality_rules)
    
    # 2. Discovery
    disco_output = None
    if discovery_contract:
        disco_engine = DiscoveryEngine(chunk_df)
        disco_output = disco_engine.run_all(discovery_contract)
        
    return {
        "val_results": val_output["results"],
        "disco_results": disco_output,
        "sample_df": chunk_df.iloc[:5].copy() if len(chunk_df) > 0 else chunk_df
    }
