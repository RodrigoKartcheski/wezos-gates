import pandas as pd
import sys
try:
    from sentinel_gate.core.discovery_engine import DiscoveryEngine
    df = pd.read_csv(r'C:\Temp\executavel\sentinel_gate\tests\sample_data\sample_data.csv')
    engine = DiscoveryEngine(df)
    result = engine.detect_primary_keys()
    print(f"Rows: {len(df)}")
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
