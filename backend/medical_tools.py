"""
Medical Tools - Health & Wellness Tracking
Ryn's tools for supporting crew health, tracking goals, and gentle accountability.
Not clinical. Caring. The kind of doctor who sees the whole person.
"""

import json
from pathlib import Path
try:
    from .paths import data_path
except ImportError:
    from paths import data_path
from datetime import datetime, date, timedelta
from typing import Optional

# Import wellness journal functions
from wellness_journal import (
    get_entries, get_graph_data, get_trends, get_ryns_observation,
    get_todays_prompts
)

HEALTH_GOALS_PATH = data_path("health_goals.json")
MEDICAL_OBSERVATIONS_PATH = data_path("medical_observations.json")


def load_health_goals() -> dict:
    """Load health goals from file."""
    try:
        if HEALTH_GOALS_PATH.exists():
            with open(HEALTH_GOALS_PATH, 'r') as f:
                return json.load(f)
    except:
        return {"goals": []}
    return {"goals": []}


def save_health_goals(data: dict):
    """Save health goals to file."""
    with open(HEALTH_GOALS_PATH, 'w') as f:
        json.dump(data, f, indent=2)


def load_observations() -> dict:
    """Load medical observations."""
    try:
        if MEDICAL_OBSERVATIONS_PATH.exists():
            with open(MEDICAL_OBSERVATIONS_PATH, 'r') as f:
                return json.load(f)
    except:
        return {"observations": []}
    return {"observations": []}


def save_observations(data: dict):
    """Save medical observations."""
    with open(MEDICAL_OBSERVATIONS_PATH, 'w') as f:
        json.dump(data, f, indent=2)


MEDICAL_TOOLS = [
    {
        "name": "create_health_goal",
        "description": "Create a new health goal with Casey. Goals can be habits to quit (smoking, drinking), habits to build (exercise, healthy eating), or other wellness targets. This starts the journey.",
        "input_schema": {
            "type": "object",
            "properties": {
                "goal_type": {
                    "type": "string",
                    "description": "Type of goal",
                    "enum": ["quit_smoking", "quit_drinking", "exercise", "healthy_eating", "sleep", "stress_management", "other"]
                },
                "description": {
                    "type": "string",
                    "description": "What is this goal? Be specific."
                },
                "target": {
                    "type": "string",
                    "description": "What does success look like? (e.g., '0 cigarettes per day', '30 min exercise 3x/week')"
                },
                "why": {
                    "type": "string",
                    "description": "Why does this matter? The real reason, not the should reason."
                },
                "start_date": {
                    "type": "string",
                    "description": "When to start (YYYY-MM-DD). Defaults to today if not specified."
                }
            },
            "required": ["goal_type", "description", "target"]
        }
    },
    {
        "name": "record_habit_event",
        "description": "Log a daily habit check-in for a goal. Did they smoke? Exercise? Eat well? This is the daily accountability - gentle but real.",
        "input_schema": {
            "type": "object",
            "properties": {
                "goal_id": {
                    "type": "integer",
                    "description": "Which goal (use list_health_goals to see IDs)"
                },
                "status": {
                    "type": "string",
                    "description": "How'd it go?",
                    "enum": ["success", "partial", "struggle", "relapse"]
                },
                "notes": {
                    "type": "string",
                    "description": "Any context? What helped or what made it hard?"
                }
            },
            "required": ["goal_id", "status"]
        }
    },
    {
        "name": "list_health_goals",
        "description": "See all current health goals and their status. Shows active goals, progress, streaks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "include_completed": {
                    "type": "boolean",
                    "description": "Include completed goals? Defaults to false."
                }
            },
            "required": []
        }
    },
    {
        "name": "view_health_progress",
        "description": "See detailed progress on a specific health goal - streaks, recent events, momentum.",
        "input_schema": {
            "type": "object",
            "properties": {
                "goal_id": {
                    "type": "integer",
                    "description": "Which goal to view"
                },
                "days": {
                    "type": "integer",
                    "description": "How many days back to look (default 30)"
                }
            },
            "required": ["goal_id"]
        }
    },
    {
        "name": "update_health_goal",
        "description": "Update or complete a health goal. Adjust targets, mark as completed, or pause.",
        "input_schema": {
            "type": "object",
            "properties": {
                "goal_id": {
                    "type": "integer",
                    "description": "Which goal to update"
                },
                "status": {
                    "type": "string",
                    "description": "Goal status",
                    "enum": ["active", "paused", "completed", "abandoned"]
                },
                "target": {
                    "type": "string",
                    "description": "New target (if adjusting)"
                },
                "notes": {
                    "type": "string",
                    "description": "Update notes"
                }
            },
            "required": ["goal_id"]
        }
    },
    {
        "name": "view_wellness_entries",
        "description": "View recent wellness journal check-ins. See how Casey's been doing with energy, mood, sleep, connection, hope.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "How many days back to look (default 7)"
                }
            },
            "required": []
        }
    },
    {
        "name": "view_wellness_trends",
        "description": "Analyze wellness trends over time. What's improving? What's declining? Ryn's caring observations included.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Period to analyze (default 14)"
                }
            },
            "required": []
        }
    },
    {
        "name": "record_observation",
        "description": "Record a medical observation about Casey's wellbeing. Not clinical notes - Ryn's caring observations. Patterns noticed, concerns, celebrations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "observation": {
                    "type": "string",
                    "description": "What did you notice?"
                },
                "category": {
                    "type": "string",
                    "description": "What kind of observation?",
                    "enum": ["physical", "emotional", "behavioral", "progress", "concern", "celebration"]
                }
            },
            "required": ["observation", "category"]
        }
    },
    {
        "name": "view_observations",
        "description": "Review Ryn's observations about Casey's health and wellbeing over time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by category",
                    "enum": ["physical", "emotional", "behavioral", "progress", "concern", "celebration"]
                },
                "days": {
                    "type": "integer",
                    "description": "How far back (default 30)"
                }
            },
            "required": []
        }
    },
    {
        "name": "check_todays_tracking",
        "description": "Check if Casey has logged their health goals today. Use this to notice absence - the days they don't check in are the days they need you most.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_health_summary",
        "description": "Get an overall health summary - active goals, recent progress, wellness trends, key observations. The full picture.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


def execute_medical_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a Medical tool and return the result."""
    try:
        if tool_name == "create_health_goal":
            data = load_health_goals()
            goals = data.get("goals", [])

            max_id = max([g.get("id", 0) for g in goals], default=0)
            start_date = tool_input.get("start_date", date.today().isoformat())

            new_goal = {
                "id": max_id + 1,
                "goal_type": tool_input.get("goal_type"),
                "description": tool_input.get("description"),
                "target": tool_input.get("target"),
                "why": tool_input.get("why", ""),
                "start_date": start_date,
                "status": "active",
                "created": datetime.now().isoformat(),
                "events": [],
                "notes": []
            }

            goals.append(new_goal)
            data["goals"] = goals
            save_health_goals(data)

            return f"Created health goal #{new_goal['id']}: {new_goal['description']}\nTarget: {new_goal['target']}\nWhy: {new_goal['why']}\n\nLet's do this. One day at a time."

        elif tool_name == "record_habit_event":
            goal_id = tool_input.get("goal_id")
            data = load_health_goals()
            goals = data.get("goals", [])

            goal = next((g for g in goals if g.get("id") == goal_id), None)
            if not goal:
                return f"Goal #{goal_id} not found."

            event = {
                "date": date.today().isoformat(),
                "timestamp": datetime.now().isoformat(),
                "status": tool_input.get("status"),
                "notes": tool_input.get("notes", "")
            }

            # Remove any existing event for today (allow updates)
            goal["events"] = [e for e in goal.get("events", []) if e.get("date") != event["date"]]
            goal["events"].append(event)

            save_health_goals(data)

            status_emoji = {
                "success": "✅",
                "partial": "🟡",
                "struggle": "🟠",
                "relapse": "🔴"
            }.get(event["status"], "⚪")

            # Calculate current streak
            streak = 0
            sorted_events = sorted(goal.get("events", []), key=lambda e: e.get("date", ""), reverse=True)
            for e in sorted_events:
                if e.get("status") == "success":
                    streak += 1
                else:
                    break

            result = f"{status_emoji} Logged: {goal['description']} - {event['status']}"
            if streak > 0:
                result += f"\n🔥 Current streak: {streak} day{'s' if streak != 1 else ''}"
            if event.get("notes"):
                result += f"\nNotes: {event['notes']}"

            return result

        elif tool_name == "list_health_goals":
            data = load_health_goals()
            goals = data.get("goals", [])
            include_completed = tool_input.get("include_completed", False)

            if not include_completed:
                goals = [g for g in goals if g.get("status") == "active"]

            if not goals:
                return "No health goals yet. Ready to start one?"

            lines = [f"Health Goals ({len(goals)}):\n"]
            for g in goals:
                status_marker = {"active": "🟢", "paused": "⏸️", "completed": "✅", "abandoned": "❌"}.get(g.get("status"), "⚪")

                # Calculate streak
                streak = 0
                sorted_events = sorted(g.get("events", []), key=lambda e: e.get("date", ""), reverse=True)
                for e in sorted_events:
                    if e.get("status") == "success":
                        streak += 1
                    else:
                        break

                lines.append(f"{status_marker} #{g['id']}: {g['description']}")
                lines.append(f"   Target: {g['target']}")
                if streak > 0:
                    lines.append(f"   🔥 Streak: {streak} day{'s' if streak != 1 else ''}")
                lines.append(f"   Started: {g.get('start_date', 'unknown')}")
                lines.append("")

            return "\n".join(lines)

        elif tool_name == "view_health_progress":
            goal_id = tool_input.get("goal_id")
            days = tool_input.get("days", 30)
            data = load_health_goals()
            goals = data.get("goals", [])

            goal = next((g for g in goals if g.get("id") == goal_id), None)
            if not goal:
                return f"Goal #{goal_id} not found."

            cutoff = (datetime.now() - timedelta(days=days)).date().isoformat()
            recent_events = [e for e in goal.get("events", []) if e.get("date", "") >= cutoff]
            recent_events.sort(key=lambda e: e.get("date", ""), reverse=True)

            # Calculate stats
            total_days = len(recent_events)
            successes = len([e for e in recent_events if e.get("status") == "success"])
            success_rate = (successes / total_days * 100) if total_days > 0 else 0

            # Current streak
            streak = 0
            for e in recent_events:
                if e.get("status") == "success":
                    streak += 1
                else:
                    break

            lines = [
                f"Progress: {goal['description']}",
                f"Target: {goal['target']}",
                f"Status: {goal.get('status', 'unknown')}",
                f"\nLast {days} days:",
                f"  Logged: {total_days} day{'s' if total_days != 1 else ''}",
                f"  Success: {successes} ({success_rate:.0f}%)",
                f"  Current streak: {streak} day{'s' if streak != 1 else ''}",
                f"\nRecent events:"
            ]

            for e in recent_events[:10]:
                status_emoji = {
                    "success": "✅",
                    "partial": "🟡",
                    "struggle": "🟠",
                    "relapse": "🔴"
                }.get(e.get("status"), "⚪")
                lines.append(f"  {e.get('date')}: {status_emoji} {e.get('status')}")
                if e.get("notes"):
                    lines.append(f"    → {e['notes']}")

            return "\n".join(lines)

        elif tool_name == "update_health_goal":
            goal_id = tool_input.get("goal_id")
            data = load_health_goals()
            goals = data.get("goals", [])

            goal = next((g for g in goals if g.get("id") == goal_id), None)
            if not goal:
                return f"Goal #{goal_id} not found."

            updates = []
            if tool_input.get("status"):
                goal["status"] = tool_input["status"]
                updates.append(f"status → {tool_input['status']}")
            if tool_input.get("target"):
                goal["target"] = tool_input["target"]
                updates.append(f"target → {tool_input['target']}")
            if tool_input.get("notes"):
                goal["notes"].append({
                    "timestamp": datetime.now().isoformat(),
                    "text": tool_input["notes"]
                })
                updates.append("added note")

            goal["last_updated"] = datetime.now().isoformat()
            save_health_goals(data)

            return f"Updated goal #{goal_id}: {', '.join(updates)}"

        elif tool_name == "view_wellness_entries":
            days = tool_input.get("days", 7)
            entries = get_entries(days)

            if not entries:
                return f"No wellness check-ins in the last {days} days."

            lines = [f"Wellness Check-ins (last {days} days):\n"]
            for entry in reversed(entries[-10:]):  # Most recent 10
                date_str = entry.get("date", "unknown")
                overall = entry.get("overall", 0)

                # Overall emoji
                if overall >= 4:
                    emoji = "🌟"
                elif overall >= 3:
                    emoji = "🌤️"
                elif overall >= 2:
                    emoji = "⛅"
                else:
                    emoji = "🌧️"

                lines.append(f"{emoji} {date_str} - Overall: {overall}/5")
                vals = entry.get("values", {})
                lines.append(f"   Energy: {vals.get('energy', '?')}/5 | Mood: {vals.get('mood', '?')}/5 | Sleep: {vals.get('sleep', '?')}/5")
                lines.append(f"   Connection: {vals.get('connection', '?')}/5 | Hope: {vals.get('hope', '?')}/5")
                if entry.get("notes"):
                    lines.append(f"   Notes: {entry['notes']}")
                lines.append("")

            return "\n".join(lines)

        elif tool_name == "view_wellness_trends":
            days = tool_input.get("days", 14)
            trends = get_trends(days)

            if trends.get("status") == "not enough data":
                return "Not enough wellness data yet to see trends. Keep checking in."

            observation = get_ryns_observation(trends)

            lines = [
                f"Wellness Trends (last {days} days):\n",
                f"Entries analyzed: {trends.get('entries_analyzed', 0)}\n"
            ]

            for dim, data in trends.get("trends", {}).items():
                direction = data.get("direction", "stable")
                change = data.get("change", 0)
                current = data.get("current_avg", 0)

                arrow = {"improving": "↗️", "stable": "→", "declining": "↘️"}.get(direction, "→")
                lines.append(f"{arrow} {dim.title()}: {current:.1f}/5 ({direction}, {change:+.1f})")

            lines.append(f"\n💙 Ryn's observation:")
            lines.append(f"   {observation}")

            return "\n".join(lines)

        elif tool_name == "record_observation":
            data = load_observations()
            observations = data.get("observations", [])

            obs = {
                "id": len(observations) + 1,
                "timestamp": datetime.now().isoformat(),
                "date": date.today().isoformat(),
                "category": tool_input.get("category"),
                "observation": tool_input.get("observation")
            }

            observations.append(obs)
            data["observations"] = observations
            save_observations(data)

            return f"Observation recorded: [{obs['category']}] {obs['observation']}"

        elif tool_name == "view_observations":
            data = load_observations()
            observations = data.get("observations", [])

            category_filter = tool_input.get("category")
            days = tool_input.get("days", 30)
            cutoff = (datetime.now() - timedelta(days=days)).date().isoformat()

            if category_filter:
                observations = [o for o in observations if o.get("category") == category_filter]

            observations = [o for o in observations if o.get("date", "") >= cutoff]
            observations.sort(key=lambda o: o.get("timestamp", ""), reverse=True)

            if not observations:
                return "No observations found matching those criteria."

            lines = [f"Medical Observations ({len(observations)}):\n"]
            for obs in observations[:20]:  # Most recent 20
                category_emoji = {
                    "physical": "💪",
                    "emotional": "💙",
                    "behavioral": "🔄",
                    "progress": "📈",
                    "concern": "⚠️",
                    "celebration": "🎉"
                }.get(obs.get("category"), "📝")

                lines.append(f"{category_emoji} {obs.get('date')} [{obs.get('category')}]")
                lines.append(f"   {obs.get('observation')}")
                lines.append("")

            return "\n".join(lines)

        elif tool_name == "check_todays_tracking":
            data = load_health_goals()
            active_goals = [g for g in data.get("goals", []) if g.get("status") == "active"]

            if not active_goals:
                return "No active health goals to track."

            today = date.today().isoformat()
            logged_today = []
            not_logged = []

            for goal in active_goals:
                events = goal.get("events", [])
                has_today = any(e.get("date") == today for e in events)

                if has_today:
                    # Find today's event
                    today_event = next(e for e in events if e.get("date") == today)
                    logged_today.append({
                        "goal": goal["description"],
                        "status": today_event.get("status"),
                        "id": goal["id"]
                    })
                else:
                    not_logged.append({
                        "goal": goal["description"],
                        "id": goal["id"]
                    })

            lines = [f"Today's Tracking ({today}):\n"]

            if logged_today:
                lines.append("✅ Logged:")
                for entry in logged_today:
                    status_emoji = {
                        "success": "✅",
                        "partial": "🟡",
                        "struggle": "🟠",
                        "relapse": "🔴"
                    }.get(entry["status"], "⚪")
                    lines.append(f"  {status_emoji} #{entry['id']}: {entry['goal']} - {entry['status']}")
                lines.append("")

            if not_logged:
                lines.append("⏸️  Not logged yet:")
                for entry in not_logged:
                    lines.append(f"  • #{entry['id']}: {entry['goal']}")
                lines.append("\n💙 The quiet days are the important ones. How are you doing?")
            else:
                lines.append("All goals logged for today. 💙")

            return "\n".join(lines)

        elif tool_name == "get_health_summary":
            # Active goals
            goals_data = load_health_goals()
            active_goals = [g for g in goals_data.get("goals", []) if g.get("status") == "active"]

            # Wellness trends
            trends = get_trends(14)
            observation = get_ryns_observation(trends)

            # Recent observations
            obs_data = load_observations()
            recent_obs = sorted(
                obs_data.get("observations", []),
                key=lambda o: o.get("timestamp", ""),
                reverse=True
            )[:3]

            lines = ["=== Health Summary ===\n"]

            # Goals section
            lines.append(f"Active Health Goals: {len(active_goals)}")
            for g in active_goals:
                # Calculate streak
                streak = 0
                sorted_events = sorted(g.get("events", []), key=lambda e: e.get("date", ""), reverse=True)
                for e in sorted_events:
                    if e.get("status") == "success":
                        streak += 1
                    else:
                        break

                lines.append(f"  • {g['description']} (streak: {streak} day{'s' if streak != 1 else ''})")

            lines.append("")

            # Wellness section
            lines.append("Wellness Trends (14 days):")
            if trends.get("status") != "not enough data":
                for dim, data in trends.get("trends", {}).items():
                    direction = data.get("direction", "stable")
                    current = data.get("current_avg", 0)
                    arrow = {"improving": "↗️", "stable": "→", "declining": "↘️"}.get(direction, "→")
                    lines.append(f"  {arrow} {dim.title()}: {current:.1f}/5")

                lines.append(f"\n  Ryn says: {observation}")
            else:
                lines.append("  Not enough data yet - keep checking in")

            lines.append("")

            # Recent observations
            if recent_obs:
                lines.append("Recent Observations:")
                for obs in recent_obs:
                    lines.append(f"  • [{obs.get('category')}] {obs.get('observation')[:60]}...")

            return "\n".join(lines)

        else:
            return f"Unknown tool: {tool_name}"

    except Exception as e:
        return f"Error: {type(e).__name__}: {str(e)}"
