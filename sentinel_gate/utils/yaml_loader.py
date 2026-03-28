import yaml
import os
from typing import Any, Dict

def load_yaml(file_path: str) -> Dict[str, Any]:
    """Loads a YAML file and returns its content as a dictionary."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Config file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        # Using SafeLoader to prevent arbitrary code execution
        return yaml.safe_load(f)

def save_yaml(data: Any, file_path: str) -> None:
    """Saves data to a YAML file."""
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True)
