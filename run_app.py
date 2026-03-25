import streamlit.web.cli as stcli
import os, sys

def resolve_path(path):
    if getattr(sys, '_MEIPASS', False):
        return os.path.join(sys._MEIPASS, path)
    return os.path.join(os.path.abspath("."), path)

if __name__ == "__main__":
    # If the first argument is 'start', route to the collector CLI instead of Streamlit
    if len(sys.argv) > 1 and sys.argv[1] == "start":
        from cli import main as cli_main
        sys.exit(cli_main())
        
    # Otherwise, launch Streamlit dashboard
    sys.argv = [
        "streamlit",
        "run",
        resolve_path("app.py"),
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())
