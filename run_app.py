import streamlit.web.cli as stcli
import os, sys

from runtime_patches import apply_streamlit_runtime_patches

def resolve_path(path):
    if getattr(sys, '_MEIPASS', False):
        return os.path.join(sys._MEIPASS, path)
    return os.path.join(os.path.abspath("."), path)

if __name__ == "__main__":
    # If the first argument is 'start', route to the collector CLI instead of Streamlit
    if len(sys.argv) > 1 and sys.argv[1] == "start":
        from cli import main as cli_main
        sys.exit(cli_main())
    if len(sys.argv) > 1 and sys.argv[1] == "cpu-temp-worker":
        from collectors.cpu_temperature_worker import main as worker_main
        sys.exit(worker_main(sys.argv[2:]))
        
    # Otherwise, launch Streamlit dashboard
    apply_streamlit_runtime_patches()
    sys.argv = [
        "streamlit",
        "run",
        resolve_path("app.py"),
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())
