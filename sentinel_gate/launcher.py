import sys
import os
import multiprocessing
import traceback

# TOTAL OVERRIDE of importlib.metadata for frozen environment
if getattr(sys, 'frozen', False):
    import importlib.metadata
    
    # Mock Distribution class
    class MockDistribution:
        def __init__(self, name, version):
            self.version = version
            self.metadata = {'Name': name, 'Version': version}
            self.entry_points = []
        def read_text(self, filename): return None
        def locate_file(self, path): return path

    _orig_distribution = importlib.metadata.distribution
    def _patched_distribution(package):
        try:
            return _orig_distribution(package)
        except Exception:
            # Fallbacks for core Streamlit dependencies
            versions = {
                'streamlit': '1.41.1',
                'ydata-profiling': '4.18.1',
                'evidently': '0.4.30',
                'pydantic': '2.10.6',
                'pydantic-core': '2.27.2'
            }
            if package in versions:
                return MockDistribution(package, versions[package])
            raise importlib.metadata.PackageNotFoundError(package)
    
    importlib.metadata.distribution = _patched_distribution
    
    # Also patch version() directly for brevity
    def _patched_version(package):
        return _patched_distribution(package).version
    importlib.metadata.version = _patched_version

# Set Streamlit UI environment variables
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
os.environ["STREAMLIT_SERVER_PORT"] = "8501"
os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"

def main():
    multiprocessing.freeze_support()
    from sentinel_gate.interfaces.cli import run_cli
    run_cli()

if __name__ == "__main__":
    main()
