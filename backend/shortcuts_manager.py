"""
Shortcuts Manager - Dynamic Tool Launcher
Allows users to add custom executable shortcuts to any section
"""

import json
import subprocess
import os
from pathlib import Path
try:
    from .paths import data_path
except ImportError:
    from paths import data_path
from typing import List, Dict, Optional

SHORTCUTS_FILE = data_path("shortcuts.json")


def load_shortcuts() -> Dict:
    """Load shortcuts from JSON file."""
    if not SHORTCUTS_FILE.exists():
        return {"shortcuts": []}

    try:
        with open(SHORTCUTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[Shortcuts] Error loading: {e}")
        return {"shortcuts": []}


def save_shortcuts(data: Dict) -> bool:
    """Save shortcuts to JSON file."""
    try:
        with open(SHORTCUTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"[Shortcuts] Error saving: {e}")
        return False


def launch_shortcut(shortcut_id: str) -> Dict:
    """Launch a shortcut by ID."""
    data = load_shortcuts()
    shortcut = next((s for s in data.get("shortcuts", []) if s["id"] == shortcut_id), None)

    if not shortcut:
        return {"success": False, "error": "Shortcut not found"}

    path = Path(shortcut["path"])

    if not path.exists():
        return {"success": False, "error": f"Path not found: {path}"}

    try:
        # Determine how to launch based on file extension
        ext = path.suffix.lower()

        if ext == ".py":
            # Python script
            subprocess.Popen(
                ["python", str(path)],
                cwd=str(path.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        elif ext in [".exe", ".bat", ".cmd"]:
            # Executable or batch file
            subprocess.Popen(
                [str(path)],
                cwd=str(path.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        elif ext == ".ps1":
            # PowerShell script
            subprocess.Popen(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(path)],
                cwd=str(path.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            # Try to open with default application
            if os.name == 'nt':  # Windows
                os.startfile(str(path))
            else:  # Unix-like
                subprocess.Popen(["xdg-open", str(path)])

        return {"success": True, "message": f"Launched {shortcut['label']}"}

    except Exception as e:
        return {"success": False, "error": f"Launch failed: {e}"}


def add_shortcut(shortcut: Dict) -> Dict:
    """Add a new shortcut."""
    data = load_shortcuts()

    # Generate ID if not provided
    if "id" not in shortcut:
        shortcut["id"] = f"shortcut-{len(data['shortcuts']) + 1}"

    # Check for duplicate ID
    if any(s["id"] == shortcut["id"] for s in data["shortcuts"]):
        return {"success": False, "error": "Shortcut ID already exists"}

    # Set defaults
    shortcut.setdefault("icon", "●")
    shortcut.setdefault("description", "")
    shortcut.setdefault("style", {"shape": "square", "color": "cyan", "size": "medium"})
    shortcut.setdefault("position", {"x": 5, "y": 5})
    shortcut.setdefault("showLabel", "hover")

    data["shortcuts"].append(shortcut)

    if save_shortcuts(data):
        return {"success": True, "shortcut": shortcut}
    else:
        return {"success": False, "error": "Failed to save"}


def update_shortcut(shortcut_id: str, updates: Dict) -> Dict:
    """Update an existing shortcut."""
    data = load_shortcuts()
    shortcut = next((s for s in data["shortcuts"] if s["id"] == shortcut_id), None)

    if not shortcut:
        return {"success": False, "error": "Shortcut not found"}

    # Update fields
    for key, value in updates.items():
        if key != "id":  # Don't allow ID changes
            shortcut[key] = value

    if save_shortcuts(data):
        return {"success": True, "shortcut": shortcut}
    else:
        return {"success": False, "error": "Failed to save"}


def delete_shortcut(shortcut_id: str) -> Dict:
    """Delete a shortcut."""
    data = load_shortcuts()
    original_count = len(data["shortcuts"])
    data["shortcuts"] = [s for s in data["shortcuts"] if s["id"] != shortcut_id]

    if len(data["shortcuts"]) == original_count:
        return {"success": False, "error": "Shortcut not found"}

    if save_shortcuts(data):
        return {"success": True, "message": "Shortcut deleted"}
    else:
        return {"success": False, "error": "Failed to save"}
