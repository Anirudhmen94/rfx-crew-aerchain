"""
streamlit_app.py — root entrypoint for Streamlit Community Cloud.
Sets up sys.path so crew_pipeline and agents are importable,
then re-executes the actual UI module in the same process.
"""
import os
import sys

# Make the repo root importable BEFORE any other import
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Now import and run the UI — Streamlit re-uses this module's globals,
# so we exec the file directly in the current namespace (same as Streamlit
# running it as __main__) rather than using runpy which creates an isolated dict.
_ui_path = os.path.join(ROOT, "ui", "app.py")
with open(_ui_path, "r", encoding="utf-8") as _f:
    exec(compile(_f.read(), _ui_path, "exec"), {"__file__": _ui_path, "__name__": "__main__"})
