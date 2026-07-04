#!/usr/bin/env python3
"""
Claude Hub - Launch Script
Start the hub server and optionally open the browser
"""

import os
import sys
import webbrowser
import time
import subprocess
from pathlib import Path


def main():
    # Get the directory containing this script
    hub_dir = Path(__file__).parent.absolute()

    # Change to hub directory
    os.chdir(hub_dir)

    # Check for dependencies
    try:
        import fastapi
        import uvicorn
        import psutil
    except ImportError:
        print("Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Dependencies installed. Please run again.")
        return

    # Start the server
    print("""
    CLAUDE HUB v0.1.0
    "Spaceship Cozy" Command Center
    """)

    # Get local IP for phone access
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "your-ip"

    print(f"Starting server on http://localhost:8767")
    print(f"Phone access: http://{local_ip}:8767")
    print("Press Ctrl+C to stop\n")

    # Open browser after a short delay
    def open_browser():
        time.sleep(1.5)
        webbrowser.open("http://localhost:8767")

    import threading
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # Run the server
    import uvicorn
    uvicorn.run(
        "backend.server:app",
        host="0.0.0.0",
        port=8767,
        reload=True,
        log_level="info",
        access_log=False  # Suppress per-request spam
    )


if __name__ == "__main__":
    main()
