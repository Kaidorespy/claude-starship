# Science Tools

**File:** `backend/science_tools.py`
**Purpose:** Project management tools for Mira

---

## Overview

Science Tools gives Mira the ability to manage projects - Casey's project tracker integrated into the ship. Mira can create projects, add contributors, track progress, and manage the board through conversation.

---

## Project Schema

```python
PROJECT_SCHEMA = {
    "id": int,
    "name": str,
    "status": str,  # planning, active, paused, mystery, complete
    "priority": str,  # high, medium, low
    "description": str,
    "createdBy": str,
    "contributors": List[{
        "id": str,
        "name": str,
        "role": str  # owner, contributor, advisor
    }],
    "comments": List[{
        "author": str,
        "text": str,
        "timestamp": str
    }],
    "updates": List[{
        "by": str,
        "action": str,
        "timestamp": str
    }],
    "tags": List[str]
}
```

---

## Available Tools

### list_projects

```python
def list_projects(status: str = None) -> List[dict]:
    """List all projects, optionally filtered by status."""
```

### get_project

```python
def get_project(project_id: int) -> dict:
    """Get detailed info about a specific project."""
```

### create_project

```python
def create_project(
    name: str,
    description: str,
    status: str = "planning",
    priority: str = "medium",
    created_by: str = "mira",
    tags: List[str] = None
) -> dict:
    """Create a new project."""
```

### update_project

```python
def update_project(
    project_id: int,
    name: str = None,
    description: str = None,
    status: str = None,
    priority: str = None
) -> dict:
    """Update project fields."""
```

### add_contributor

```python
def add_contributor(
    project_id: int,
    contributor_id: str,
    contributor_name: str,
    role: str = "contributor"
) -> dict:
    """Add someone to a project."""
```

### add_comment

```python
def add_comment(
    project_id: int,
    author: str,
    text: str
) -> dict:
    """Add a comment to a project."""
```

### get_activity

```python
def get_activity(project_id: int = None, limit: int = 20) -> List[dict]:
    """Get activity log. If no project_id, returns all activity."""
```

### add_tags

```python
def add_tags(project_id: int, tags: List[str]) -> dict:
    """Add tags to a project."""
```

---

## Tool Schemas for Claude

```python
SCIENCE_TOOL_SCHEMAS = [
    {
        "name": "list_projects",
        "description": "List all projects on the board",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["planning", "active", "paused", "mystery", "complete"],
                    "description": "Filter by status"
                }
            }
        }
    },
    {
        "name": "create_project",
        "description": "Create a new project",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "status": {"type": "string"},
                "priority": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["name", "description"]
        }
    },
    # ... etc
]
```

---

## Data Storage

**File:** `projects.json`

```json
{
    "projects": [
        {
            "id": 1,
            "name": "Sensor Array Upgrade",
            "status": "active",
            "priority": "high",
            "description": "Improve long-range detection",
            "createdBy": "mira",
            "contributors": [
                {"id": "mira", "name": "Mira", "role": "owner"},
                {"id": "server", "name": "Alex", "role": "contributor"}
            ],
            "comments": [],
            "updates": [
                {"by": "mira", "action": "created", "timestamp": "..."}
            ],
            "tags": ["engineering", "sensors"]
        }
    ],
    "next_id": 2
}
```

---

## Integration with Server

```python
# In server.py, Science terminal uses science handler:

if terminal_id == "science":  # Mira
    async for chunk in handle_science_request(
        anthropic_client,
        messages,
        mira_system_prompt
    ):
        await websocket.send_json({
            "type": "stream",
            "data": chunk
        })
```

---

## Example Conversations

**Casey:** "Mira, can you create a project for the new navigation system?"

**Mira:**
```
*pulls up the board*

Let me create that for you.

*taps*

Done. I've created "Navigation System Overhaul" as a planning-stage project.
I've tagged it with 'nav' and 'engineering'. Priority is set to medium.

Would you like me to add anyone as contributors? Alex might be interested
given the engineering component.
```

---

**Casey:** "What's the status of our active projects?"

**Mira:**
```
*checks the board*

We have 3 active projects:

1. Sensor Array Upgrade (high priority)
   - Alex and I are on this
   - Last update: 2 days ago

2. Crew Wellness Tracking (medium)
   - Ryn is leading this one
   - Good progress

3. Holodeck Memory Archive (low)
   - More of a background project
   - Holodeck is... contributing in their way

Want details on any of these?
```

---

## Status Meanings

| Status | Meaning |
|--------|---------|
| `planning` | Still figuring it out |
| `active` | Work in progress |
| `paused` | On hold |
| `mystery` | Exploratory, unclear goals |
| `complete` | Done |

---

## Frontend Integration

The Science Lab has a visual project board:

- **New Project button** - Opens creation modal
- **View Board button** - Kanban view by status
- **Project cards** - Click for detail modal

Files: `js/project-board.js`, `css/science.css`

---

*Mira keeps track of what we're building.*
