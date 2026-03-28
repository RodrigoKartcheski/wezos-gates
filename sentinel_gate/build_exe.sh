#!/bin/bash

# Install dependencies if not present
pip install -r requirements.txt
pip install pyinstaller

# Build the executable
# --onefile: Generate a single executable
# --name: Name of the output file
# --hidden-import: Ensure dynamic imports are included
pyinstaller \
--onefile \
--name data-profiler \
--hidden-import google.cloud.bigquery \
--hidden-import ydata_profiling \
--hidden-import mcp \
--hidden-import matplotlib.backends.backend_svg \
--hidden-import matplotlib.backends.backend_pdf \
--hidden-import matplotlib.backends.backend_agg \
--collect-all ydata_profiling \
--collect-all matplotlib \
__main__.py

echo "Build complete. Executable can be found in the dist/ folder."
