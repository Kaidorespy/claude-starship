"""
BACKGROUND CREW TOOLS
File access, documentation, and project management for gamma shift.
Limited scope - they're good at their jobs, but not command material.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any

# Safe working directory (user's home or current project)
SAFE_BASE = Path.home()
PROJECT_ROOT = Path(__file__).parent.parent


def is_safe_path(path: str) -> bool:
    """Check if path is safe to access."""
    try:
        resolved = Path(path).resolve()
        # Must be within project root or user's documents/projects
        return (
            str(resolved).startswith(str(PROJECT_ROOT)) or
            str(resolved).startswith(str(SAFE_BASE / "Documents")) or
            str(resolved).startswith(str(SAFE_BASE / "projects"))
        )
    except:
        return False


BACKGROUND_CREW_TOOLS = [
    {
        "name": "read_file",
        "description": "Read contents of a file. Use this to review code, documentation, or project files before working on them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read (relative or absolute)"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write or update a file. Use this to create documentation, update project files, or write code. Be careful and thorough.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to write"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["file_path", "content"]
        }
    },
    {
        "name": "list_directory",
        "description": "List contents of a directory. Use this to explore project structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory path to list"
                }
            },
            "required": ["directory"]
        }
    },
    {
        "name": "search_files",
        "description": "Search for text patterns in files. Use this to find specific code or documentation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Text pattern to search for"
                },
                "directory": {
                    "type": "string",
                    "description": "Directory to search in (defaults to project root)"
                }
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "append_to_file",
        "description": "Append content to end of existing file. Good for adding to logs or project notes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file"
                },
                "content": {
                    "type": "string",
                    "description": "Content to append"
                }
            },
            "required": ["file_path", "content"]
        }
    },
    {
        "name": "create_project_note",
        "description": "Create a shift note or project update. This goes in the department's shift notes folder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title/subject of the note"
                },
                "content": {
                    "type": "string",
                    "description": "Note content (markdown supported)"
                },
                "department": {
                    "type": "string",
                    "description": "Department (engineering, science, medical)"
                }
            },
            "required": ["title", "content", "department"]
        }
    }
]


def execute_background_crew_tool(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """Execute a background crew tool."""

    try:
        if tool_name == "read_file":
            path = Path(tool_input["file_path"]).resolve()
            if not is_safe_path(str(path)):
                return f"Error: Access denied to {path} (outside safe directories)"
            if not path.exists():
                return f"Error: File not found: {path}"
            if not path.is_file():
                return f"Error: Not a file: {path}"

            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                return f"File: {path}\n\n{content}"

        elif tool_name == "write_file":
            path = Path(tool_input["file_path"]).resolve()
            if not is_safe_path(str(path)):
                return f"Error: Access denied to {path}"

            # Create parent directory if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                f.write(tool_input["content"])

            return f"Successfully wrote {len(tool_input['content'])} characters to {path}"

        elif tool_name == "list_directory":
            path = Path(tool_input["directory"]).resolve()
            if not is_safe_path(str(path)):
                return f"Error: Access denied to {path}"
            if not path.exists():
                return f"Error: Directory not found: {path}"
            if not path.is_dir():
                return f"Error: Not a directory: {path}"

            items = []
            for item in sorted(path.iterdir()):
                type_marker = "/" if item.is_dir() else ""
                items.append(f"{item.name}{type_marker}")

            return f"Contents of {path}:\n" + "\n".join(items)

        elif tool_name == "search_files":
            pattern = tool_input["pattern"]
            directory = tool_input.get("directory", str(PROJECT_ROOT))
            path = Path(directory).resolve()

            if not is_safe_path(str(path)):
                return f"Error: Access denied to {path}"

            # Use grep if available, otherwise Python search
            try:
                result = subprocess.run(
                    ["grep", "-r", "-n", pattern, str(path)],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    return result.stdout[:5000]  # Limit output
                else:
                    return f"No matches found for '{pattern}'"
            except:
                # Fallback: simple Python search
                matches = []
                for file_path in path.rglob("*.py"):
                    if not is_safe_path(str(file_path)):
                        continue
                    try:
                        with open(file_path, 'r') as f:
                            for i, line in enumerate(f, 1):
                                if pattern in line:
                                    matches.append(f"{file_path}:{i}: {line.strip()}")
                                    if len(matches) >= 50:
                                        break
                    except:
                        pass

                return "\n".join(matches[:50]) if matches else f"No matches found for '{pattern}'"

        elif tool_name == "append_to_file":
            path = Path(tool_input["file_path"]).resolve()
            if not is_safe_path(str(path)):
                return f"Error: Access denied to {path}"

            with open(path, 'a', encoding='utf-8') as f:
                f.write(tool_input["content"])

            return f"Appended to {path}"

        elif tool_name == "create_project_note":
            dept = tool_input["department"]
            title = tool_input["title"]
            content = tool_input["content"]

            # Create department notes directory if needed
            notes_dir = PROJECT_ROOT / "shift_notes" / dept
            notes_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename from title
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"{timestamp}_{title.replace(' ', '_').lower()}.md"
            file_path = notes_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {title}\n\n")
                f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
                f.write(content)

            return f"Created shift note: {file_path}"

        else:
            return f"Error: Unknown tool '{tool_name}'"

    except Exception as e:
        return f"Error executing {tool_name}: {str(e)}"
