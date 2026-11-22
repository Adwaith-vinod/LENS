"""
Main entry point for the LENS Backend Server.
"""
import uvicorn
import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def start_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False):
    print("=" * 60)
    print("  LENS: AI-Powered Intelligent Local File Discovery")
    print(f"  Server starting at http://{host}:{port}")
    print(f"  API Docs available at http://{host}:{port}/docs")
    print("=" * 60)
    uvicorn.run("backend.api.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    start_server()
