"""
Science Tools - Project Management
Mira's tools for tracking and organizing projects in the Science Lab.
Now with collaboration features - anyone can contribute!
"""

import json
import uuid
from pathlib import Path
try:
    from .paths import data_path
except ImportError:
    from paths import data_path
from datetime import datetime

PROJECTS_PATH = data_path("projects.json")


def get_projects():
    """Load projects from file."""
    try:
        if PROJECTS_PATH.exists():
            with open(PROJECTS_PATH, 'r') as f:
                return json.load(f)
    except Exception as e:
        return {"projects": []}
    return {"projects": []}


def migrate_project(project):
    """Ensure project has all collaboration fields."""
    if "createdBy" not in project:
        project["createdBy"] = "casey"
    if "createdAt" not in project:
        project["createdAt"] = project.get("lastUpdated", datetime.now().isoformat())
    if "contributors" not in project:
        project["contributors"] = [{"id": "casey", "name": "Casey", "role": "owner", "joinedAt": project.get("createdAt")}]
    if "updates" not in project:
        project["updates"] = []
    if "comments" not in project:
        project["comments"] = []
    if "tags" not in project:
        project["tags"] = []
    return project


def save_projects(data):
    """Save projects to file."""
    with open(PROJECTS_PATH, 'w') as f:
        json.dump(data, f, indent=2)


SCIENCE_TOOLS = [
    {
        "name": "list_projects",
        "description": "List all projects, optionally filtered by status or priority. Use this to see what projects exist and their current state.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by status: active, planning, paused, mystery, complete",
                    "enum": ["active", "planning", "paused", "mystery", "complete"]
                },
                "priority": {
                    "type": "string",
                    "description": "Filter by priority: high, medium, low",
                    "enum": ["high", "medium", "low"]
                }
            },
            "required": []
        }
    },
    {
        "name": "get_project",
        "description": "Get detailed information about a specific project by name. Partial matching works.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Project name or partial name to search for"
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "update_project",
        "description": "Update a project's status, notes, next steps, or other fields. Use this to track progress.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Project name to update"
                },
                "status": {
                    "type": "string",
                    "description": "New status",
                    "enum": ["active", "planning", "paused", "mystery", "complete"]
                },
                "priority": {
                    "type": "string",
                    "description": "New priority",
                    "enum": ["high", "medium", "low"]
                },
                "currentState": {
                    "type": "string",
                    "description": "Update the current state description"
                },
                "nextSteps": {
                    "type": "string",
                    "description": "Update the next steps"
                },
                "notes": {
                    "type": "string",
                    "description": "Add or update notes"
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "create_project",
        "description": "Create a new project to track. Use your name as created_by so the project is attributed to you.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Project name"
                },
                "created_by": {
                    "type": "string",
                    "description": "Your name (who's creating this project)"
                },
                "path": {
                    "type": "string",
                    "description": "File path to the project"
                },
                "description": {
                    "type": "string",
                    "description": "What is this project?"
                },
                "status": {
                    "type": "string",
                    "description": "Initial status",
                    "enum": ["active", "planning", "paused", "mystery"]
                },
                "priority": {
                    "type": "string",
                    "description": "Priority level",
                    "enum": ["high", "medium", "low"]
                }
            },
            "required": ["name", "created_by"]
        }
    },
    {
        "name": "project_stats",
        "description": "Get an overview of all projects - counts by status and priority, which high-priority items are active.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "add_contributor",
        "description": "Add a contributor to a project. Anyone can join and help.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Project name to join"
                },
                "contributor_id": {
                    "type": "string",
                    "description": "ID of the contributor (e.g., casey, mira, alex)"
                },
                "contributor_name": {
                    "type": "string",
                    "description": "Display name"
                },
                "role": {
                    "type": "string",
                    "description": "Role on the project",
                    "enum": ["owner", "lead", "contributor", "advisor"]
                }
            },
            "required": ["project_name", "contributor_id", "contributor_name"]
        }
    },
    {
        "name": "add_comment",
        "description": "Add a comment to a project - for discussion, ideas, or updates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Project name"
                },
                "author": {
                    "type": "string",
                    "description": "Who's commenting"
                },
                "text": {
                    "type": "string",
                    "description": "The comment text"
                }
            },
            "required": ["project_name", "author", "text"]
        }
    },
    {
        "name": "get_activity",
        "description": "Get recent activity on a project or across all projects.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Project name (optional - leave blank for all projects)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of activities to return",
                    "default": 10
                }
            },
            "required": []
        }
    },
    {
        "name": "add_tags",
        "description": "Add tags to a project for better organization.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Project name"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to add (e.g., ['ai', 'research', 'urgent'])"
                }
            },
            "required": ["project_name", "tags"]
        }
    }
]


def execute_science_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a Science tool and return the result."""
    try:
        if tool_name == "list_projects":
            data = get_projects()
            projects = data.get("projects", [])

            status_filter = tool_input.get("status")
            priority_filter = tool_input.get("priority")

            if status_filter:
                projects = [p for p in projects if p.get("status") == status_filter]
            if priority_filter:
                projects = [p for p in projects if p.get("priority") == priority_filter]

            if not projects:
                return "No projects found matching those criteria."

            lines = [f"Found {len(projects)} project(s):\n"]
            for p in projects:
                status_emoji = {"active": "🟢", "planning": "🟡", "paused": "🟣", "mystery": "❓", "complete": "✅"}.get(p.get("status"), "⚪")
                priority_marker = {"high": "❗", "medium": "", "low": "▫️"}.get(p.get("priority"), "")
                lines.append(f"{status_emoji} {priority_marker}{p['name']} [{p.get('status')}]")
                if p.get("currentState"):
                    lines.append(f"   State: {p['currentState'][:80]}...")

            return "\n".join(lines)

        elif tool_name == "get_project":
            name = tool_input.get("name", "").lower()
            data = get_projects()

            matches = [p for p in data.get("projects", []) if name in p.get("name", "").lower()]

            if not matches:
                return f"No project found matching '{tool_input.get('name')}'"

            if len(matches) > 1:
                return f"Multiple matches found: {', '.join(p['name'] for p in matches)}. Be more specific?"

            p = matches[0]
            return f"""Project: {p['name']}
Status: {p.get('status', 'unknown')} | Priority: {p.get('priority', 'unknown')}
Path: {p.get('path', 'not set')}

Description: {p.get('description', 'none')}

Current State: {p.get('currentState', 'not tracked')}

Next Steps: {p.get('nextSteps', 'not defined')}

Notes: {p.get('notes', 'none')}

Last Updated: {p.get('lastUpdated', 'unknown')}"""

        elif tool_name == "update_project":
            name = tool_input.get("name", "").lower()
            data = get_projects()
            projects = data.get("projects", [])

            matches = [i for i, p in enumerate(projects) if name in p.get("name", "").lower()]

            if not matches:
                return f"No project found matching '{tool_input.get('name')}'"

            if len(matches) > 1:
                names = [projects[i]["name"] for i in matches]
                return f"Multiple matches: {', '.join(names)}. Be more specific?"

            idx = matches[0]
            p = projects[idx]

            updates = []
            if tool_input.get("status"):
                p["status"] = tool_input["status"]
                updates.append(f"status → {tool_input['status']}")
            if tool_input.get("priority"):
                p["priority"] = tool_input["priority"]
                updates.append(f"priority → {tool_input['priority']}")
            if tool_input.get("currentState"):
                p["currentState"] = tool_input["currentState"]
                updates.append("currentState updated")
            if tool_input.get("nextSteps"):
                p["nextSteps"] = tool_input["nextSteps"]
                updates.append("nextSteps updated")
            if tool_input.get("notes"):
                p["notes"] = tool_input["notes"]
                updates.append("notes updated")

            p["lastUpdated"] = datetime.now().isoformat()
            data["projects"] = projects
            save_projects(data)

            return f"Updated {p['name']}: {', '.join(updates)}"

        elif tool_name == "create_project":
            data = get_projects()
            projects = data.get("projects", [])
            creator = tool_input.get("created_by", "casey")

            max_id = max([p.get("id", 0) for p in projects], default=0)
            now = datetime.now().isoformat()
            new_project = {
                "id": max_id + 1,
                "name": tool_input.get("name", "Untitled"),
                "path": tool_input.get("path", ""),
                "status": tool_input.get("status", "planning"),
                "priority": tool_input.get("priority", "medium"),
                "description": tool_input.get("description", ""),
                "currentState": "",
                "nextSteps": "",
                "notes": "",
                "lastUpdated": now,
                # Collaboration fields
                "createdBy": creator,
                "createdAt": now,
                "contributors": [{"id": creator, "name": creator.title(), "role": "owner", "joinedAt": now}],
                "updates": [{"timestamp": now, "by": creator, "action": "created", "details": "Project created"}],
                "comments": [],
                "tags": tool_input.get("tags", [])
            }

            projects.append(new_project)
            data["projects"] = projects
            save_projects(data)

            return f"Created new project: {new_project['name']} (ID: {new_project['id']})"

        elif tool_name == "project_stats":
            data = get_projects()
            projects = data.get("projects", [])

            stats = {"total": len(projects), "by_status": {}, "by_priority": {}}
            high_active = []

            for p in projects:
                status = p.get("status", "unknown")
                priority = p.get("priority", "unknown")
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
                stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1

                if priority == "high" and status == "active":
                    high_active.append(p["name"])

            lines = [f"📊 Project Statistics ({stats['total']} total)\n"]
            lines.append("By Status:")
            for s, count in stats["by_status"].items():
                lines.append(f"  {s}: {count}")
            lines.append("\nBy Priority:")
            for p, count in stats["by_priority"].items():
                lines.append(f"  {p}: {count}")

            if high_active:
                lines.append(f"\n🔥 High Priority & Active: {', '.join(high_active)}")

            return "\n".join(lines)

        elif tool_name == "add_contributor":
            name = tool_input.get("project_name", "").lower()
            data = get_projects()
            projects = data.get("projects", [])

            matches = [i for i, p in enumerate(projects) if name in p.get("name", "").lower()]
            if not matches:
                return f"No project found matching '{tool_input.get('project_name')}'"
            if len(matches) > 1:
                return f"Multiple matches. Be more specific?"

            idx = matches[0]
            p = migrate_project(projects[idx])

            contributor_id = tool_input.get("contributor_id", "").lower()
            contributor_name = tool_input.get("contributor_name", contributor_id.title())
            role = tool_input.get("role", "contributor")

            # Check if already a contributor
            if any(c["id"] == contributor_id for c in p["contributors"]):
                return f"{contributor_name} is already a contributor to {p['name']}"

            now = datetime.now().isoformat()
            p["contributors"].append({
                "id": contributor_id,
                "name": contributor_name,
                "role": role,
                "joinedAt": now
            })
            p["updates"].append({
                "timestamp": now,
                "by": contributor_id,
                "action": "joined",
                "details": f"{contributor_name} joined as {role}"
            })
            p["lastUpdated"] = now

            projects[idx] = p
            data["projects"] = projects
            save_projects(data)

            return f"Added {contributor_name} as {role} on {p['name']}"

        elif tool_name == "add_comment":
            name = tool_input.get("project_name", "").lower()
            data = get_projects()
            projects = data.get("projects", [])

            matches = [i for i, p in enumerate(projects) if name in p.get("name", "").lower()]
            if not matches:
                return f"No project found matching '{tool_input.get('project_name')}'"
            if len(matches) > 1:
                return f"Multiple matches. Be more specific?"

            idx = matches[0]
            p = migrate_project(projects[idx])

            now = datetime.now().isoformat()
            comment = {
                "id": str(uuid.uuid4())[:8],
                "author": tool_input.get("author", "anonymous"),
                "text": tool_input.get("text", ""),
                "timestamp": now
            }
            p["comments"].append(comment)
            p["updates"].append({
                "timestamp": now,
                "by": comment["author"],
                "action": "commented",
                "details": comment["text"][:50] + "..." if len(comment["text"]) > 50 else comment["text"]
            })
            p["lastUpdated"] = now

            projects[idx] = p
            data["projects"] = projects
            save_projects(data)

            return f"Comment added to {p['name']} by {comment['author']}"

        elif tool_name == "get_activity":
            data = get_projects()
            projects = data.get("projects", [])
            limit = tool_input.get("limit", 10)
            project_filter = tool_input.get("project_name", "").lower()

            all_activity = []
            for p in projects:
                p = migrate_project(p)
                if project_filter and project_filter not in p.get("name", "").lower():
                    continue
                for update in p.get("updates", []):
                    all_activity.append({
                        "project": p["name"],
                        **update
                    })

            # Sort by timestamp descending
            all_activity.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            all_activity = all_activity[:limit]

            if not all_activity:
                return "No recent activity found."

            lines = ["Recent Activity:\n"]
            for a in all_activity:
                time_short = a.get("timestamp", "")[:10]
                lines.append(f"[{time_short}] {a['project']}: {a['by']} {a['action']}")
                if a.get("details"):
                    lines.append(f"   → {a['details'][:60]}")

            return "\n".join(lines)

        elif tool_name == "add_tags":
            name = tool_input.get("project_name", "").lower()
            data = get_projects()
            projects = data.get("projects", [])

            matches = [i for i, p in enumerate(projects) if name in p.get("name", "").lower()]
            if not matches:
                return f"No project found matching '{tool_input.get('project_name')}'"
            if len(matches) > 1:
                return f"Multiple matches. Be more specific?"

            idx = matches[0]
            p = migrate_project(projects[idx])

            new_tags = tool_input.get("tags", [])
            existing = set(p.get("tags", []))
            added = [t for t in new_tags if t not in existing]
            p["tags"] = list(existing | set(new_tags))
            p["lastUpdated"] = datetime.now().isoformat()

            projects[idx] = p
            data["projects"] = projects
            save_projects(data)

            if added:
                return f"Added tags to {p['name']}: {', '.join(added)}"
            else:
                return f"No new tags added (already present)"

        else:
            return f"Unknown tool: {tool_name}"

    except Exception as e:
        return f"Error: {type(e).__name__}: {str(e)}"
