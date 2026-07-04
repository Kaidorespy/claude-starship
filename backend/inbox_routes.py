"""
Inbox API Routes - Async crew<->Casey messaging
"""

from fastapi import APIRouter
from pathlib import Path
try:
    from .paths import data_path
except ImportError:
    from paths import data_path
import json

from message_system import (
    add_message, add_message_to_casey, get_messages,
    get_casey_inbox, get_casey_inbox_by_crew, get_casey_inbox_summary,
    mark_message_read, mark_casey_message_read, mark_all_read,
    has_unread, get_inbox_summary, load_messages, save_messages
)

router = APIRouter()


@router.get("/inbox")
async def get_inbox():
    """Get Casey's inbox - messages from crew, organized by sender."""
    by_crew = get_casey_inbox_by_crew()
    summary = get_casey_inbox_summary()
    return {
        "messages_by_crew": by_crew,
        "summary": summary,
    }


@router.get("/inbox/summary")
async def get_inbox_summary_endpoint():
    """Get summary of inbox state (unread counts per crew)."""
    return get_casey_inbox_summary()


@router.get("/inbox/{crew_id}")
async def get_crew_messages(crew_id: str, limit: int = 20):
    """Get messages from a specific crew member to Casey."""
    messages = get_casey_inbox(limit=limit, crew_filter=crew_id)
    return {
        "crew_id": crew_id,
        "messages": messages,
    }


@router.post("/inbox/{crew_id}/send")
async def send_message_to_crew(crew_id: str, text: str, context: str = ""):
    """Casey sends a message to a crew member."""
    message = add_message(crew_id, "casey", text, context)
    return {"success": True, "message": message}


@router.post("/inbox/mark-read/{message_id}")
async def mark_inbox_message_read(message_id: str):
    """Mark a message in Casey's inbox as read."""
    success = mark_casey_message_read(message_id)
    return {"success": success}


@router.post("/inbox/{crew_id}/mark-all-read")
async def mark_all_crew_messages_read(crew_id: str):
    """Mark all messages from a crew member as read."""
    data = load_messages()
    count = 0
    if "casey_inbox" in data:
        for msg in data["casey_inbox"]:
            if msg["from"] == crew_id and not msg["read"]:
                msg["read"] = True
                count += 1
        if count > 0:
            save_messages(data)
    return {"success": True, "marked": count}


@router.get("/ship-log/recent")
async def get_recent_ship_log(limit: int = 50):
    """Get recent ship log entries for RSS-style display."""
    try:
        log_file = data_path("ship_log.json")
        if log_file.exists():
            with open(log_file, 'r') as f:
                log = json.load(f)
            return {"entries": list(reversed(log[-limit:]))}
    except Exception as e:
        print(f"[Ship Log] Error reading log: {e}", flush=True)
    return {"entries": []}
