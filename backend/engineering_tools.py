"""Engineering tools for local file and command access."""

import subprocess
from pathlib import Path

try:
    from .trust_system import can_crew_do
except ImportError:
    from trust_system import can_crew_do


def is_path_allowed(path: str) -> tuple[bool, str]:
    """Path checks are capability-based; scoped path allowlists come later."""
    return True, "ok"


def is_command_allowed(command: str) -> tuple[bool, str]:
    """Command checks are capability-based; command allowlists come later."""
    return True, "ok"


def can_use_tool(tool_name: str) -> tuple[bool, str]:
    """Check current ship controls before exposing a real local tool."""
    capability_by_tool = {
        "list_directory": "see_file_tree",
        "read_file": "read_files",
        "write_file": "full_access",
        "execute_command": "run_commands",
    }
    capability = capability_by_tool.get(tool_name)
    if not capability or can_crew_do(capability):
        return True, "ok"
    return False, "Tool unavailable"


ENGINEERING_TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file from Casey's computer. Use this to examine code, configs, logs, or any text file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute or relative path to the file to read"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file on Casey's computer. Creates the file if it doesn't exist, overwrites if it does.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute or relative path to the file to write"
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "execute_command",
        "description": "Execute a shell command on Casey's computer. Use this to run scripts, install packages, check system status, git operations, etc. Be thoughtful - this runs for real.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute"
                },
                "working_directory": {
                    "type": "string",
                    "description": "Optional working directory for the command"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "list_directory",
        "description": "List contents of a directory on Casey's computer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the directory to list"
                }
            },
            "required": ["path"]
        }
    }
]


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute an Engineering tool and return the result."""
    try:
        allowed, reason = can_use_tool(tool_name)
        if not allowed:
            return f"Error: {reason}"

        if tool_name == "read_file":
            path = tool_input["path"]

            # Security check
            allowed, reason = is_path_allowed(path)
            if not allowed:
                return f"Error: {reason}"

            path = Path(path).expanduser()
            if not path.exists():
                return f"Error: File not found: {path}"
            content = path.read_text(encoding='utf-8', errors='replace')
            # Truncate if too long
            if len(content) > 50000:
                content = content[:50000] + "\n\n... [truncated, file too large]"
            return content

        elif tool_name == "write_file":
            path = tool_input["path"]

            # Security check
            allowed, reason = is_path_allowed(path)
            if not allowed:
                return f"Error: {reason}"

            path = Path(path).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(tool_input["content"], encoding='utf-8')
            return f"Successfully wrote {len(tool_input['content'])} characters to {path}"

        elif tool_name == "execute_command":
            cmd = tool_input["command"]

            # Security check
            allowed, reason = is_command_allowed(cmd)
            if not allowed:
                return f"Error: {reason}"

            cwd = tool_input.get("working_directory")
            if cwd:
                # Check working directory is allowed
                allowed, reason = is_path_allowed(cwd)
                if not allowed:
                    return f"Error: Working directory - {reason}"
                cwd = Path(cwd).expanduser()

            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=cwd
            )

            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            if result.returncode != 0:
                output += f"\n[exit code: {result.returncode}]"

            return output if output.strip() else "[command completed with no output]"

        elif tool_name == "list_directory":
            path = tool_input["path"]

            # Security check
            allowed, reason = is_path_allowed(path)
            if not allowed:
                return f"Error: {reason}"

            path = Path(path).expanduser()
            if not path.exists():
                return f"Error: Directory not found: {path}"
            if not path.is_dir():
                return f"Error: Not a directory: {path}"

            items = []
            for item in sorted(path.iterdir()):
                prefix = "[DIR] " if item.is_dir() else "      "
                items.append(f"{prefix}{item.name}")

            return "\n".join(items) if items else "[empty directory]"

        else:
            return f"Error: Unknown tool: {tool_name}"

    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 120 seconds"
    except Exception as e:
        return f"Error: {type(e).__name__}: {str(e)}"
