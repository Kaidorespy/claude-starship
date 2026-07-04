#!/usr/bin/env python3
"""
Quick preview server - just serves the frontend statically.
Use this to see the UI without the full backend.
"""

import http.server
import socketserver
import webbrowser
import os
from pathlib import Path

PORT = 8080

# Change to frontend directory
frontend_dir = Path(__file__).parent / "frontend"
os.chdir(frontend_dir)

# Handler defined inline below

print(f"""
    CLAUDE HUB - Preview Mode
    (UI only, terminals in demo mode)

    Opening http://localhost:{PORT}
    Press Ctrl+C to stop
""")

# Open browser
webbrowser.open(f"http://localhost:{PORT}")

with socketserver.TCPServer(("", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
