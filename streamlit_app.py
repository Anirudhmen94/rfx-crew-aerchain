# streamlit_app.py — root entrypoint for Streamlit Community Cloud deployment
# Streamlit Cloud expects the main file at repo root by default.

import runpy, os, sys

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

# Run the actual app
runpy.run_path(os.path.join(os.path.dirname(__file__), "ui", "app.py"), run_name="__main__")
