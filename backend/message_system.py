"""
Message System - Async crew<->Casey communication without ping pressure.

Messages are low-priority, no trust penalty, persist until read.
Separate from pings which are urgent and trust-weighted.
"""

import json
from datetime import datetime
from pathlib import Path
try:
    from .paths import data_path
except ImportError:
    from paths import data_path
from typing import Optional, List

MESSAGES_FILE = data_path("crew_messages.json")

# Crew display names for consistency
CREW_DISPLAY_NAMES = {
    "claude": "Lumen",
    "server": "Alex",
    "personal": "DQ",
    "science": "Mira",
    "games": "Holodeck",
    "med": "Ryn",
    "rec": "The Bartender",
}


def load_messages() -> dict:
    """Load messages from file."""
    if MESSAGES_FILE.exists():
        try:
            with open(MESSAGES_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    # Initialize with empty message lists for each crew
    return {
        "claude": [],
        "server": [],
        "personal": [],
        "science": [],
        "games": [],
        "med": [],
        "rec": [],
    }


def save_messages(data: dict):
    """Save messages to file."""
    with open(MESSAGES_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def add_message(crew_id: str, sender: str, text: str, context: str = "") -> dict:
    """
    Add a message to a crew member's inbox.

    Args:
        crew_id: The crew member's terminal ID
        sender: "casey" or crew_id of sender
        text: The message content
        context: Optional context (what this is about)

    Returns:
        The created message dict
    """
    data = load_messages()

    if crew_id not in data:
        data[crew_id] = []

    message = {
        "id": f"msg_{datetime.now().timestamp()}",
        "from": sender,
        "from_name": "Casey" if sender == "casey" else CREW_DISPLAY_NAMES.get(sender, sender),
        "text": text,
        "context": context,
        "timestamp": datetime.now().isoformat(),
        "read": False,
    }

    data[crew_id].append(message)

    # Keep only last 50 messages per crew (oldest unread stay, oldest read drop)
    if len(data[crew_id]) > 50:
        # Separate read and unread
        unread = [m for m in data[crew_id] if not m["read"]]
        read = [m for m in data[crew_id] if m["read"]]

        # If we have more than 20 unread, drop oldest unread
        if len(unread) > 20:
            unread = unread[-20:]

        # Fill remaining slots with most recent read messages
        remaining_slots = 50 - len(unread)
        read = read[-remaining_slots:] if remaining_slots > 0 else []

        # Combine and sort by timestamp
        data[crew_id] = sorted(unread + read, key=lambda m: m["timestamp"])

    save_messages(data)

    sender_name = "Casey" if sender == "casey" else CREW_DISPLAY_NAMES.get(sender, sender)
    recipient_name = CREW_DISPLAY_NAMES.get(crew_id, crew_id)
    print(f"[Message] {sender_name} → {recipient_name}: {text[:50]}...", flush=True)

    return message


def get_messages(crew_id: str, limit: int = 20) -> List[dict]:
    """Get messages for a crew member, most recent first."""
    data = load_messages()
    messages = data.get(crew_id, [])
    # Return most recent first
    return list(reversed(messages[-limit:]))


def get_unread_messages(crew_id: str) -> List[dict]:
    """Get only unread messages for a crew member."""
    data = load_messages()
    messages = data.get(crew_id, [])
    return [m for m in messages if not m["read"]]


def mark_message_read(crew_id: str, message_id: str) -> bool:
    """Mark a specific message as read."""
    data = load_messages()

    if crew_id not in data:
        return False

    for message in data[crew_id]:
        if message["id"] == message_id:
            message["read"] = True
            save_messages(data)
            return True

    return False


def mark_all_read(crew_id: str) -> int:
    """Mark all messages for a crew member as read. Returns count marked."""
    data = load_messages()

    if crew_id not in data:
        return 0

    count = 0
    for message in data[crew_id]:
        if not message["read"]:
            message["read"] = True
            count += 1

    if count > 0:
        save_messages(data)

    return count


def has_unread(crew_id: str) -> bool:
    """Check if crew member has any unread messages."""
    data = load_messages()
    messages = data.get(crew_id, [])
    return any(not m["read"] for m in messages)


def get_inbox_summary() -> dict:
    """Get summary of all inboxes (for UI state)."""
    data = load_messages()
    summary = {}

    for crew_id in data:
        messages = data[crew_id]
        unread = [m for m in messages if not m["read"]]
        summary[crew_id] = {
            "total": len(messages),
            "unread": len(unread),
            "has_new": len(unread) > 0,
            "latest": messages[-1]["timestamp"] if messages else None,
        }

    return summary


def get_casey_unread() -> List[dict]:
    """
    Get all unread messages TO Casey (from crew).
    These are messages where sender != "casey".
    """
    data = load_messages()
    casey_messages = []

    for crew_id, messages in data.items():
        for msg in messages:
            # Messages from crew to Casey are stored in crew's inbox with sender = crew_id
            # We need a different approach - messages TO casey should be in a casey inbox
            pass

    # Actually, let's store Casey's inbox separately
    return data.get("casey_inbox", [])


def add_message_to_casey(crew_id: str, text: str, context: str = "") -> dict:
    """
    Crew member sends a message to Casey.
    Stored in casey_inbox key.
    """
    data = load_messages()

    if "casey_inbox" not in data:
        data["casey_inbox"] = []

    message = {
        "id": f"msg_{datetime.now().timestamp()}",
        "from": crew_id,
        "from_name": CREW_DISPLAY_NAMES.get(crew_id, crew_id),
        "text": text,
        "context": context,
        "timestamp": datetime.now().isoformat(),
        "read": False,
    }

    data["casey_inbox"].append(message)

    # Keep only last 100 messages to Casey (more since it's aggregated)
    if len(data["casey_inbox"]) > 100:
        # Keep unread priority
        unread = [m for m in data["casey_inbox"] if not m["read"]]
        read = [m for m in data["casey_inbox"] if m["read"]]

        if len(unread) > 50:
            unread = unread[-50:]

        remaining = 100 - len(unread)
        read = read[-remaining:] if remaining > 0 else []

        data["casey_inbox"] = sorted(unread + read, key=lambda m: m["timestamp"])

    save_messages(data)

    crew_name = CREW_DISPLAY_NAMES.get(crew_id, crew_id)
    print(f"[Message] {crew_name} → Casey: {text[:50]}...", flush=True)

    return message


def get_casey_inbox(limit: int = 20, crew_filter: str = None) -> List[dict]:
    """
    Get messages sent to Casey from crew.

    Args:
        limit: Max messages to return
        crew_filter: If provided, only return messages from this crew_id
    """
    data = load_messages()
    messages = data.get("casey_inbox", [])

    if crew_filter:
        messages = [m for m in messages if m["from"] == crew_filter]

    # Most recent first
    return list(reversed(messages[-limit:]))


def get_casey_inbox_by_crew() -> dict:
    """
    Get Casey's inbox organized by crew member.
    Returns dict of crew_id -> list of messages.
    """
    data = load_messages()
    messages = data.get("casey_inbox", [])

    by_crew = {}
    for msg in messages:
        crew_id = msg["from"]
        if crew_id not in by_crew:
            by_crew[crew_id] = []
        by_crew[crew_id].append(msg)

    # Sort each crew's messages by timestamp (most recent last for display)
    for crew_id in by_crew:
        by_crew[crew_id] = sorted(by_crew[crew_id], key=lambda m: m["timestamp"])

    return by_crew


def mark_casey_message_read(message_id: str) -> bool:
    """Mark a message in Casey's inbox as read."""
    data = load_messages()

    if "casey_inbox" not in data:
        return False

    for message in data["casey_inbox"]:
        if message["id"] == message_id:
            message["read"] = True
            save_messages(data)
            return True

    return False


def get_casey_inbox_summary() -> dict:
    """Get summary of Casey's inbox by crew member."""
    by_crew = get_casey_inbox_by_crew()

    summary = {}
    for crew_id, messages in by_crew.items():
        unread = [m for m in messages if not m["read"]]
        summary[crew_id] = {
            "total": len(messages),
            "unread": len(unread),
            "has_new": len(unread) > 0,
            "crew_name": CREW_DISPLAY_NAMES.get(crew_id, crew_id),
            "latest": messages[-1] if messages else None,
        }

    return summary
