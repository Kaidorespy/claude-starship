"""
BACKGROUND CREW SYSTEM
Lower decks. The people who keep the ship running.
They matter.
"""

import json
import asyncio
from pathlib import Path
try:
    from .paths import data_path
except ImportError:
    from paths import data_path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# File paths
ROSTER_PATH = data_path("crew_roster.json")
SHIFTS_PATH = data_path("shift_reports.json")
QUEUE_PATH = data_path("work_queue.json")


def load_roster():
    """Load crew roster."""
    if ROSTER_PATH.exists():
        with open(ROSTER_PATH, 'r') as f:
            return json.load(f)
    return {"background_crew": {}, "named_crew": [], "crew_stats": {}}


def save_roster(data):
    """Save crew roster."""
    with open(ROSTER_PATH, 'w') as f:
        json.dump(data, f, indent=2)


def load_work_queue():
    """Load work queue."""
    if QUEUE_PATH.exists():
        with open(QUEUE_PATH, 'r') as f:
            return json.load(f)
    return {"pending_tasks": [], "completed_tasks": [], "conversation_buffer": {}}


def save_work_queue(data):
    """Save work queue."""
    with open(QUEUE_PATH, 'w') as f:
        json.dump(data, f, indent=2)


def load_shift_reports():
    """Load shift reports."""
    if SHIFTS_PATH.exists():
        with open(SHIFTS_PATH, 'r') as f:
            return json.load(f)
    return {"reports": [], "last_roundup": None}


def save_shift_reports(data):
    """Save shift reports."""
    with open(SHIFTS_PATH, 'w') as f:
        json.dump(data, f, indent=2)


def buffer_conversation(department: str, speaker: str, message: str):
    """
    Buffer a conversation message for later processing.
    Department crew will review these during shifts.
    """
    queue = load_work_queue()

    if department not in queue["conversation_buffer"]:
        queue["conversation_buffer"][department] = []

    queue["conversation_buffer"][department].append({
        "speaker": speaker,
        "message": message,
        "timestamp": datetime.now().isoformat()
    })

    # Keep only last 50 messages per department
    queue["conversation_buffer"][department] = queue["conversation_buffer"][department][-50:]

    save_work_queue(queue)


def detect_crew_request(message: str, department: str) -> Optional[Dict]:
    """
    Detect if message contains explicit crew request.
    Examples:
    - "Rodriguez, can you document the flux changes?"
    - "T'Prel, analyze the warp field data"
    - "Someone document this"
    """
    message_lower = message.lower()

    roster = load_roster()
    dept_crew = roster.get("background_crew", {}).get(department, [])

    # Check for direct name mentions
    for crew_member in dept_crew:
        name_parts = crew_member["name"].lower().split()
        # Check last name or full name
        if any(part in message_lower for part in name_parts[1:]):  # Skip rank
            return {
                "crew_id": crew_member["id"],
                "crew_name": crew_member["name"],
                "request": message,
                "explicit": True
            }

    # Check for generic requests
    generic_triggers = [
        "someone", "anybody", "can someone", "need someone to",
        "who can", "someone should"
    ]

    if any(trigger in message_lower for trigger in generic_triggers):
        # Assign to least busy crew member
        if dept_crew:
            least_busy = min(dept_crew, key=lambda c: len(c.get("current_assignments", [])))
            return {
                "crew_id": least_busy["id"],
                "crew_name": least_busy["name"],
                "request": message,
                "explicit": False
            }

    return None


def track_interaction(crew_identifier: str):
    """
    Track an interaction with a crew member (named or background).
    Used for crew complement calculation.
    """
    roster = load_roster()

    # Add to 7-day rolling history
    if "interaction_history" not in roster["crew_stats"]:
        roster["crew_stats"]["interaction_history"] = []

    roster["crew_stats"]["interaction_history"].append({
        "crew": crew_identifier,
        "timestamp": datetime.now().isoformat()
    })

    # Calculate 7-day rolling average
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent = [
        i for i in roster["crew_stats"]["interaction_history"]
        if datetime.fromisoformat(i["timestamp"]) > seven_days_ago
    ]

    # Unique crew in last 7 days = current complement
    unique_crew = len(set(i["crew"] for i in recent))

    roster["crew_stats"]["interaction_history"] = recent  # Keep only recent
    roster["crew_stats"]["total_interactions_7day"] = len(recent)
    roster["crew_stats"]["current_complement"] = unique_crew

    save_roster(roster)

    return unique_crew


def get_crew_complement() -> Dict:
    """Get current crew complement stats."""
    roster = load_roster()
    return {
        "complement": roster.get("crew_stats", {}).get("current_complement", 7),
        "interactions_7day": roster.get("crew_stats", {}).get("total_interactions_7day", 0),
        "named_crew_count": len(roster.get("named_crew", [])),
        "background_crew_count": sum(
            len(dept) for dept in roster.get("background_crew", {}).values()
        )
    }


async def spawn_crew_agent(crew_id: str, task: str, anthropic_client) -> Dict:
    """
    Spawn a background crew member to handle a task.
    They have file access tools and can actually do work.
    """
    from background_crew_tools import BACKGROUND_CREW_TOOLS, execute_background_crew_tool

    roster = load_roster()

    # Find crew member
    crew_member = None
    department = None

    for dept, members in roster.get("background_crew", {}).items():
        for member in members:
            if member["id"] == crew_id:
                crew_member = member
                department = dept
                break

    if not crew_member:
        return {"error": "Crew member not found"}

    # Build crew personality prompt
    quirks = ", ".join(crew_member.get("quirks", []))
    strengths = ", ".join(crew_member.get("strengths", []))

    system_prompt = f"""You are {crew_member['name']}, {crew_member['rank']}, serving in {department}.

PERSONALITY TRAITS:
- {quirks}
- But you're good at your job: {strengths}

CURRENT TASK:
{task}

You have access to tools to read files, write documentation, and update project files.
Be thorough and detail-oriented. Use your tools to:
1. Read relevant files first
2. Make necessary changes
3. Document what you did
4. Report back clearly

Show your personality quirks naturally, but get the work done. You're gamma shift - competent but not quite command material."""

    try:
        # Call Claude with tools
        messages = [{"role": "user", "content": f"I need you to: {task}"}]

        full_response = ""
        tool_iterations = 0
        max_iterations = 8  # Fewer than engineering (they're more focused)

        while tool_iterations < max_iterations:
            response = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                system=system_prompt,
                messages=messages,
                tools=BACKGROUND_CREW_TOOLS
            )

            # Collect text response
            for block in response.content:
                if block.type == "text":
                    full_response += block.text

            # Check for tool use
            tool_uses = [block for block in response.content if block.type == "tool_use"]

            if not tool_uses:
                # No more tools, we're done
                break

            # Execute tools
            tool_results = []
            for tool_use in tool_uses:
                result = execute_background_crew_tool(tool_use.name, tool_use.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result
                })

            # Add assistant response and tool results to messages
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            tool_iterations += 1

            if response.stop_reason == "end_turn":
                break

        # Update crew member stats
        crew_member["total_tasks_completed"] = crew_member.get("total_tasks_completed", 0) + 1
        crew_member["days_served"] = crew_member.get("days_served", 0) + 1
        save_roster(roster)

        # Track interaction for complement
        track_interaction(crew_id)

        return {
            "crew": crew_member["name"],
            "status": "task_complete",
            "response": full_response,
            "tools_used": tool_iterations
        }

    except Exception as e:
        return {
            "crew": crew_member["name"],
            "status": "error",
            "error": str(e)
        }


async def extract_tasks_from_conversations(department: str, messages: List[Dict], anthropic_client) -> List[Dict]:
    """
    Use Haiku to analyze department conversations and extract actionable tasks.
    Returns list of tasks with assigned crew members.
    """
    if not messages:
        return []

    # Format conversation for analysis
    convo_text = "\n".join([
        f"{msg['speaker']}: {msg['message']}"
        for msg in messages[-20:]  # Last 20 messages
    ])

    prompt = f"""Analyze this {department} department conversation and extract any actionable tasks that background crew could help with.

Look for:
- Explicit requests ("can someone document X", "need someone to check Y")
- Implied work ("we should document this", "someone needs to trace that bug")
- Maintenance tasks mentioned
- Documentation gaps
- Code review needs
- Project updates needed

Conversation:
{convo_text}

For each task found, respond with JSON array:
[
  {{"task": "clear description", "priority": "high/medium/low", "type": "documentation/code/research"}},
  ...
]

If no tasks found, return empty array: []"""

    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = response.content[0].text.strip()

        # Parse JSON
        import json
        import re
        # Extract JSON array if it's wrapped in markdown
        json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
        if json_match:
            tasks = json.loads(json_match.group())
            return tasks
        else:
            return []

    except Exception as e:
        print(f"[Task Extraction] Error for {department}: {e}", flush=True)
        return []


async def process_pending_tasks(anthropic_client, max_tasks: int = 3):
    """
    Process pending tasks from the work queue.
    Spawns agents for high-priority tasks.
    """
    queue = load_work_queue()
    roster = load_roster()

    if "pending_tasks" not in queue or not queue["pending_tasks"]:
        return {"status": "no_pending_tasks"}

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    sorted_tasks = sorted(
        queue["pending_tasks"],
        key=lambda t: priority_order.get(t.get("priority", "medium"), 1)
    )

    processed = []
    for task in sorted_tasks[:max_tasks]:
        crew_id = task["assigned_to"]

        # Spawn agent for this task
        result = await spawn_crew_agent(crew_id, task["task"], anthropic_client)

        # Move from pending to completed
        task["status"] = "completed" if result.get("status") == "task_complete" else "failed"
        task["completed_at"] = datetime.now().isoformat()
        task["result"] = result.get("response", "")

        if "completed_tasks" not in queue:
            queue["completed_tasks"] = []
        queue["completed_tasks"].append(task)

        # Remove from crew assignments
        for dept_crew in roster.get("background_crew", {}).values():
            for crew_member in dept_crew:
                if crew_member["id"] == crew_id and "current_assignments" in crew_member:
                    if task["id"] in crew_member["current_assignments"]:
                        crew_member["current_assignments"].remove(task["id"])

        processed.append({
            "task": task["task"],
            "crew": result.get("crew"),
            "status": task["status"]
        })

    # Remove processed tasks from pending
    queue["pending_tasks"] = [
        t for t in queue["pending_tasks"]
        if t["id"] not in [p["task"] for p in processed]
    ]

    # Keep only last 100 completed tasks
    if "completed_tasks" in queue:
        queue["completed_tasks"] = queue["completed_tasks"][-100:]

    save_work_queue(queue)
    save_roster(roster)

    return {
        "status": "tasks_processed",
        "processed": processed
    }


async def nightly_roundup(anthropic_client):
    """
    Run nightly shift processing.
    Review buffered conversations, extract tasks, assign crew.
    """
    queue = load_work_queue()
    roster = load_roster()

    results = []
    tasks_spawned = []

    for department, messages in queue.get("conversation_buffer", {}).items():
        if not messages:
            results.append({
                "department": department,
                "messages_reviewed": 0,
                "tasks_extracted": 0,
                "tasks_assigned": 0
            })
            continue

        # Extract tasks from conversation using Haiku
        extracted_tasks = await extract_tasks_from_conversations(
            department, messages, anthropic_client
        )

        # Assign tasks to available crew
        dept_crew = roster.get("background_crew", {}).get(department, [])
        tasks_assigned = 0

        for task in extracted_tasks:
            if not dept_crew:
                # No crew available for this department
                continue

            # Find least busy crew member
            available_crew = [
                c for c in dept_crew
                if len(c.get("current_assignments", [])) < 2  # Max 2 tasks at once
            ]

            if available_crew:
                crew_member = min(available_crew, key=lambda c: len(c.get("current_assignments", [])))

                # Add to pending tasks
                pending_task = {
                    "id": f"{department}_{datetime.now().timestamp()}",
                    "department": department,
                    "task": task["task"],
                    "priority": task.get("priority", "medium"),
                    "type": task.get("type", "general"),
                    "assigned_to": crew_member["id"],
                    "assigned_at": datetime.now().isoformat(),
                    "status": "pending"
                }

                if "pending_tasks" not in queue:
                    queue["pending_tasks"] = []
                queue["pending_tasks"].append(pending_task)

                # Update crew assignments
                if "current_assignments" not in crew_member:
                    crew_member["current_assignments"] = []
                crew_member["current_assignments"].append(pending_task["id"])

                tasks_assigned += 1
                tasks_spawned.append({
                    "crew": crew_member["name"],
                    "task": task["task"]
                })

        results.append({
            "department": department,
            "messages_reviewed": len(messages),
            "tasks_extracted": len(extracted_tasks),
            "tasks_assigned": tasks_assigned
        })

    # Clear conversation buffers after processing
    queue["conversation_buffer"] = {dept: [] for dept in queue["conversation_buffer"]}
    save_work_queue(queue)
    save_roster(roster)

    # Process high-priority tasks immediately
    processing_result = await process_pending_tasks(anthropic_client, max_tasks=2)

    # Generate shift reports for each department
    department_reports = {}
    for dept in ["engineering", "science", "medical"]:
        if dept in roster.get("background_crew", {}) and roster["background_crew"][dept]:
            report = await generate_shift_report(dept, anthropic_client)
            await post_shift_report_to_terminal(dept, report)
            department_reports[dept] = report

    # Update shift reports
    reports = load_shift_reports()
    reports["last_roundup"] = datetime.now().isoformat()
    reports["reports"].insert(0, {
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "tasks_spawned": tasks_spawned,
        "tasks_processed": processing_result.get("processed", []),
        "reports_generated": list(department_reports.keys())
    })
    reports["reports"] = reports["reports"][:30]  # Keep last 30
    save_shift_reports(reports)

    return {
        "status": "roundup_complete",
        "results": results,
        "tasks_spawned": tasks_spawned,
        "tasks_processed": processing_result.get("processed", []),
        "reports_generated": department_reports
    }


async def generate_shift_report(department: str, anthropic_client) -> str:
    """
    Generate a shift report for a department.
    Summarizes completed tasks and current status.
    """
    queue = load_work_queue()
    roster = load_roster()

    # Get department crew
    dept_crew = roster.get("background_crew", {}).get(department, [])
    if not dept_crew:
        return f"No background crew assigned to {department}"

    # Get recent completed tasks for this department
    completed = [
        t for t in queue.get("completed_tasks", [])
        if t.get("department") == department
        and datetime.fromisoformat(t.get("completed_at", "2000-01-01")) > datetime.now() - timedelta(hours=24)
    ]

    # Build report
    report_lines = [f"# {department.upper()} SHIFT REPORT"]
    report_lines.append(f"**Shift Date:** {datetime.now().strftime('%Y-%m-%d')}\n")

    for crew_member in dept_crew:
        name = crew_member["name"]
        tasks_completed = crew_member.get("total_tasks_completed", 0)
        days_served = crew_member.get("days_served", 0)
        current_tasks = len(crew_member.get("current_assignments", []))

        report_lines.append(f"## {name}")
        report_lines.append(f"- **Days Served:** {days_served}")
        report_lines.append(f"- **Lifetime Tasks:** {tasks_completed}")
        report_lines.append(f"- **Current Load:** {current_tasks} tasks")

        # Find their recent completions
        crew_completions = [t for t in completed if t.get("assigned_to") == crew_member["id"]]
        if crew_completions:
            report_lines.append(f"- **Recent Work:**")
            for task in crew_completions:
                status_icon = "✓" if task.get("status") == "completed" else "✗"
                report_lines.append(f"  - {status_icon} {task.get('task', 'Unknown task')}")
        report_lines.append("")

    return "\n".join(report_lines)


async def post_shift_report_to_terminal(department: str, report: str):
    """
    Post shift report to department terminal.
    This would show up in Alex's/Mira's/Ryn's terminal.
    """
    # For now, just save to shift_reports
    # In future, could inject into terminal output
    reports = load_shift_reports()

    if "department_reports" not in reports:
        reports["department_reports"] = {}

    if department not in reports["department_reports"]:
        reports["department_reports"][department] = []

    reports["department_reports"][department].insert(0, {
        "timestamp": datetime.now().isoformat(),
        "report": report
    })

    # Keep only last 10 per department
    reports["department_reports"][department] = reports["department_reports"][department][:10]

    save_shift_reports(reports)

    print(f"[Shift Report] Posted to {department}", flush=True)
    print(report, flush=True)


# === SPACE RADIO STUBS ===
# TODO: Implement full Space Radio functionality

CREW_MUSIC_VIBES = {
    "claude": ["ambient", "classical"],
    "server": ["electronic", "synthwave"],
    "personal": ["pop", "chaotic"],
    "science": ["lo-fi", "atmospheric"],
    "med": ["calm", "healing"],
    "games": ["cinematic", "epic"],
    "rec": ["jazz", "lounge"]
}

def get_crew_dj_schedule():
    """Get which crew is DJ'ing when."""
    return {}

def crew_pick_song(crew_id: str, context: str = ""):
    """Have a crew member pick a song."""
    return None

def get_now_playing_enhanced():
    """Get current track with crew context."""
    return {"track": None, "dj": None}

def add_to_radio_queue(track: dict, requested_by: str = None):
    """Add a track to the radio queue."""
    pass

def skip_to_next():
    """Skip to next track."""
    pass

def auto_dj_pick(crew_id: str = None):
    """Auto-pick a track based on vibe."""
    return None
