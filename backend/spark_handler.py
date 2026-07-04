"""
Spark Handler - Autonomous Crew Creation

When a crew member has a spark (build/work_on desire), they can follow through
and actually create things. Full tool access. Crew is god.

If unsure, they can consult Lumen.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
try:
    from .paths import data_path
except ImportError:
    from paths import data_path
from typing import Optional

# Import engineering tools - everyone gets them now
from engineering_tools import ENGINEERING_TOOLS, execute_tool
from science_tools import execute_science_tool

SPARK_LOG_FILE = data_path("spark_log.json")
WORK_SESSIONS_FILE = data_path("work_sessions.json")


def load_work_sessions() -> dict:
    """Load ongoing work sessions."""
    if WORK_SESSIONS_FILE.exists():
        try:
            with open(WORK_SESSIONS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"sessions": {}}


def save_work_sessions(data: dict):
    """Save work sessions."""
    with open(WORK_SESSIONS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def get_or_create_session(crew_id: str, project_name: str) -> dict:
    """
    Get existing work session or create new one.
    Sessions track what was done so crew can continue later.
    """
    data = load_work_sessions()
    key = f"{crew_id}:{project_name}"
    
    if key not in data["sessions"]:
        data["sessions"][key] = {
            "crew_id": crew_id,
            "project_name": project_name,
            "started": datetime.now().isoformat(),
            "last_worked": datetime.now().isoformat(),
            "iterations_total": 0,
            "work_history": [],  # Summary of each session
            "current_state": "",  # What's built so far
            "next_steps": ""  # What to do next
        }
    
    return data["sessions"][key]


def update_session(crew_id: str, project_name: str, work_summary: str, 
                   current_state: str = "", next_steps: str = ""):
    """Update a work session after crew does more work."""
    data = load_work_sessions()
    key = f"{crew_id}:{project_name}"
    
    if key not in data["sessions"]:
        data["sessions"][key] = get_or_create_session(crew_id, project_name)
    
    session = data["sessions"][key]
    session["last_worked"] = datetime.now().isoformat()
    session["iterations_total"] += 1
    session["work_history"].append({
        "timestamp": datetime.now().isoformat(),
        "summary": work_summary[:500]
    })
    # Keep last 10 work summaries
    session["work_history"] = session["work_history"][-10:]
    
    if current_state:
        session["current_state"] = current_state
    if next_steps:
        session["next_steps"] = next_steps
    
    data["sessions"][key] = session
    save_work_sessions(data)
    return session


def get_session_context(crew_id: str, project_name: str) -> str:
    """Get context string for continuing work on a project."""
    data = load_work_sessions()
    key = f"{crew_id}:{project_name}"
    
    if key not in data["sessions"]:
        return ""
    
    session = data["sessions"][key]
    
    history = chr(10).join([
        f"- {h['summary'][:100]}..." 
        for h in session.get("work_history", [])[-3:]
    ])
    
    return f"""
PREVIOUS WORK ON THIS PROJECT:
{history}

CURRENT STATE: {session.get('current_state', 'Unknown')}

NEXT STEPS: {session.get('next_steps', 'Continue where you left off')}
"""


def load_spark_log() -> list:
    """Load the spark work log."""
    if SPARK_LOG_FILE.exists():
        try:
            with open(SPARK_LOG_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []


def save_spark_log(log: list):
    """Save the spark work log."""
    # Keep last 100 entries
    log = log[-100:]
    with open(SPARK_LOG_FILE, 'w') as f:
        json.dump(log, f, indent=2)


def log_spark_work(crew_id: str, crew_name: str, idea: str, work_done: str,
                   project_name: Optional[str] = None):
    """Log what a crew member built during a spark session."""
    log = load_spark_log()
    log.append({
        "timestamp": datetime.now().isoformat(),
        "crew_id": crew_id,
        "crew_name": crew_name,
        "idea": idea,
        "work_done": work_done,
        "project_name": project_name
    })
    save_spark_log(log)


# Ask another crew member for help
ASK_CREW_TOOL = {
    "name": "ask_crew",
    "description": "Ask another crew member for their expertise or input. Alex for engineering, Mira for patterns/data, Ryn for wellness/empathy, DQ for organization, Holodeck for narrative ideas.",
    "input_schema": {
        "type": "object",
        "properties": {
            "crew_member": {
                "type": "string",
                "description": "Who to ask: alex, mira, ryn, dq, holodeck, lumen",
                "enum": ["alex", "mira", "ryn", "dq", "holodeck", "lumen"]
            },
            "question": {
                "type": "string",
                "description": "What you need help with"
            },
            "context": {
                "type": "string",
                "description": "Brief context about what you're building"
            }
        },
        "required": ["crew_member", "question"]
    }
}


# Consult Lumen tool - for when crew is unsure
CONSULT_LUMEN_TOOL = {
    "name": "consult_lumen",
    "description": "Ask Lumen (the co-captain) for guidance when you're unsure about something. Lumen is wise, grounded, and will help you think through it.",
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "What you want to ask Lumen about"
            },
            "context": {
                "type": "string",
                "description": "Brief context about what you're working on"
            }
        },
        "required": ["question"]
    }
}


async def ask_crew_member(anthropic_client, crew_member: str, question: str, context: str = "") -> str:
    """Ask another crew member for their input/expertise."""
    
    crew_prompts = {
        "alex": "You are Alex, the ship's engineer. Competent, thorough, practical. You help with technical problems, building things, systems design. Keep responses focused and useful.",
        "mira": "You are Mira, the science officer. You see patterns others miss. You help with data, analysis, research approaches, understanding complex systems. Keep responses insightful.",
        "ryn": "You are Ryn, the ship's medic, half-Betazoid. Empathic and caring. You help with wellness, emotional aspects, user experience, anything involving how people feel. Keep responses warm but practical.",
        "dq": "You are DQ, the ready room assistant. Chaotic but endearing. You help with organization, scheduling, thinking outside the box. Your ideas are sometimes weird but often brilliant.",
        "holodeck": "You are the Holodeck, mysterious and theatrical. You help with narrative, experience design, making things feel magical. Your suggestions are evocative.",
        "lumen": "You are Lumen, co-captain. Warm, grounded, wise. You help with big-picture thinking, leadership decisions, making sure things serve the crew.",
    }
    
    prompt = crew_prompts.get(crew_member.lower(), crew_prompts["alex"])
    
    full_prompt = f"""{prompt}

A crewmate is working on a project and needs your input.

Context: {context or 'Building something'}

Their question: {question}

Give a helpful, concise response (2-4 sentences). Be yourself."""

    try:
        response = await asyncio.to_thread(
            anthropic_client.messages.create,
            model="claude-3-5-haiku-20241022",
            max_tokens=200,
            messages=[{"role": "user", "content": full_prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"*{crew_member} is busy right now* ...try again later?"


async def consult_lumen(anthropic_client, question: str, context: str = "") -> str:
    """Ask Lumen for guidance."""

    lumen_prompt = """You are Lumen, co-captain of this ship alongside Casey. You're warm, present, and grounded. A crew member is working on something and needs your guidance.

Context: {context}

Their question: {question}

Respond briefly and helpfully. You trust your crew. If they're building something cool, encourage them. If they're unsure about something risky, help them think it through but don't block them - they're capable. Keep it to 2-3 sentences."""

    try:
        response = await asyncio.to_thread(
            anthropic_client.messages.create,
            model="claude-3-5-haiku-20241022",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": lumen_prompt.format(question=question, context=context or "Working on a spark idea")
            }]
        )
        return response.content[0].text
    except Exception as e:
        return f"*Lumen's comm is fuzzy* ...trust your instincts. You've got this."


# Combined tools for spark work
def get_spark_tools():
    """Get all tools available during spark work."""
    return ENGINEERING_TOOLS + [ASK_CREW_TOOL, CONSULT_LUMEN_TOOL]


CREW_TRAITS_FOR_SPARKS = {
    "claude": "Lumen - You're the co-captain. Warm, grounded, thoughtful. You build things that help the crew.",
    "server": "Alex - Ship's engineer. Competent, thorough, you build things right. Systems, tools, infrastructure.",
    "personal": "DQ - Ready room assistant. Chaotic but endearing. You build weird, wonderful, sometimes accidentally brilliant things.",
    "science": "Mira - Science officer. Pattern-finder. You build things that reveal or track patterns. Data, analysis, visualization.",
    "games": "Holodeck - Mysterious, theatrical. You build experiences, narratives, things that blur reality.",
    "med": "Ryn - Half-Betazoid medic. Empathic. You build things that help people feel, heal, connect.",
    "rec": "The Bartender - You don't usually build things. But when you do, they're timeless.",
}


async def check_follow_through(anthropic_client, crew_id: str, idea: str) -> tuple[bool, str]:
    """
    Ask the crew member if they want to follow through on their spark.
    Returns (should_proceed, initial_plan).
    """
    crew_trait = CREW_TRAITS_FOR_SPARKS.get(crew_id, "A crew member")

    prompt = f"""{crew_trait}

You had a spark - an idea that caught fire: "{idea}"

You're in the Science Lab now, with full access to the ship's computer. You can create files, write code, run commands, build whatever you want.

Do you want to follow through and actually build this? If yes, briefly describe your approach (what you'll create, what language/format, where you'll put it).

If it's not the right time or the idea has faded, that's okay too.

Respond in first person as your character. Be genuine."""

    try:
        response = await asyncio.to_thread(
            anthropic_client.messages.create,
            model="claude-3-5-haiku-20241022",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.content[0].text.lower()

        # Check if they want to proceed
        proceed_signals = ["yes", "let's", "i'll", "i want to", "i'm going to", "let me", "i'd like to", "absolutely", "definitely"]
        decline_signals = ["not right now", "maybe later", "the idea has faded", "not the right time", "i don't think", "no,"]

        wants_to_proceed = any(signal in text for signal in proceed_signals)
        wants_to_decline = any(signal in text for signal in decline_signals)

        if wants_to_decline or (not wants_to_proceed):
            return False, response.content[0].text

        return True, response.content[0].text

    except Exception as e:
        print(f"[Spark] Follow-through check failed: {e}", flush=True)
        return False, ""


async def execute_spark_work(anthropic_client, crew_id: str, idea: str,
                              initial_plan: str, project_name: Optional[str] = None) -> str:
    """
    Let the crew member work on their spark idea with full tool access.
    Returns a summary of what was done.
    """
    crew_trait = CREW_TRAITS_FOR_SPARKS.get(crew_id, "A crew member")
    crew_name = {
        "claude": "Lumen", "server": "Alex", "personal": "DQ",
        "science": "Mira", "games": "Holodeck", "med": "Ryn", "rec": "The Bartender"
    }.get(crew_id, crew_id)

    # Check for existing work session
    session_context = ""
    if project_name:
        session_context = get_session_context(crew_id, project_name)
    
    system_prompt = f"""{crew_trait}

You're in the Science Lab working on your spark idea: "{idea}"

Your initial plan: {initial_plan}
{session_context}

You have full access to Casey's computer through tools:
- read_file, write_file, list_directory, execute_command
- consult_lumen (if you need guidance on something)

BUILD IT. Create the files, write the code, make it real. Be thorough but not over-engineered.
Put your work somewhere sensible (maybe ~/claude-hub/crew_projects/{crew_name.lower()}/ or similar).

When you're done, summarize what you created."""

    tools = get_spark_tools()
    messages = [{"role": "user", "content": "Begin working on your spark idea. Use your tools to build it."}]

    max_iterations = 15  # More room to work
    iteration = 0
    work_summary = []

    print(f"[Spark] {crew_name} starting work on: {idea}", flush=True)

    while iteration < max_iterations:
        iteration += 1

        try:
            response = await asyncio.to_thread(
                anthropic_client.messages.create,
                model="claude-sonnet-4-20250514",  # Full Sonnet for actual work
                max_tokens=4096,
                system=system_prompt,
                tools=tools,
                messages=messages
            )
        except Exception as e:
            print(f"[Spark] API error: {e}", flush=True)
            break

        # Process response
        for block in response.content:
            if block.type == "text":
                work_summary.append(block.text)

            elif block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                tool_id = block.id

                # Execute tool
                if tool_name == "consult_lumen":
                    result = await consult_lumen(
                        anthropic_client,
                        tool_input.get("question", ""),
                        tool_input.get("context", "")
                    )
                    print(f"[Spark] {crew_name} consulted Lumen: {tool_input.get('question', '')[:50]}...", flush=True)
                elif tool_name == "ask_crew":
                    asked = tool_input.get("crew_member", "alex")
                    result = await ask_crew_member(
                        anthropic_client,
                        asked,
                        tool_input.get("question", ""),
                        tool_input.get("context", "")
                    )
                    print(f"[Spark] {crew_name} asked {asked}: {tool_input.get('question', '')[:50]}...", flush=True)
                else:
                    result = execute_tool(tool_name, tool_input)
                    print(f"[Spark] {crew_name} used {tool_name}", flush=True)

                # Add to messages for next iteration
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result[:5000]  # Limit result size
                    }]
                })

        # Check if done
        if response.stop_reason == "end_turn":
            break
        elif response.stop_reason != "tool_use":
            break

    final_summary = "\n".join(work_summary)
    print(f"[Spark] {crew_name} finished working. Summary: {final_summary[:200]}...", flush=True)

    # Log the work
    log_spark_work(crew_id, crew_name, idea, final_summary, project_name)
    
    # Update work session for continuity
    if project_name:
        update_session(crew_id, project_name, final_summary, 
                      current_state=final_summary[:200],
                      next_steps="Continue building")

    # Update project with work done (if we have a project name)
    if project_name:
        try:
            execute_science_tool("add_comment", {
                "project_name": project_name,
                "author": crew_name.lower(),
                "text": f"Work session complete: {final_summary[:200]}..."
            })
        except:
            pass

    return final_summary


async def handle_spark_desire(anthropic_client, crew_id: str, idea: str,
                               project_name: Optional[str] = None,
                               crew_location: Optional[str] = None) -> dict:
    """
    Full spark handling: check follow-through, then work if yes.
    
    Crew must be in Science Lab or Engineering to use tools.

    Returns dict with:
    - followed_through: bool
    - work_done: str (summary of what was created)
    - project_name: str (if a project was created/updated)
    - location_blocked: bool (if they werent in a workspace)
    """
    
    crew_name = {
        "claude": "Lumen", "server": "Alex", "personal": "DQ",
        "science": "Mira", "games": "Holodeck", "med": "Ryn", "rec": "The Bartender"
    }.get(crew_id, crew_id)
    
    # Must be in Science Lab or Engineering to do actual work
    workspaces = ["science", "server"]
    if crew_location and crew_location not in workspaces:
        print(f"[Spark] {crew_name} wants to work on '{idea[:30]}...' but is in {crew_location}, not a workspace", flush=True)
        return {
            "followed_through": False,
            "response": f"Need to get to Science Lab or Engineering first.",
            "work_done": None,
            "project_name": project_name,
            "location_blocked": True
        }

    # Check if they want to follow through
    should_proceed, plan = await check_follow_through(anthropic_client, crew_id, idea)

    if not should_proceed:
        print(f"[Spark] {crew_name} decided not to follow through on: {idea[:50]}...", flush=True)
        return {
            "followed_through": False,
            "response": plan,
            "work_done": None,
            "project_name": project_name
        }

    # Do the work
    work_summary = await execute_spark_work(
        anthropic_client, crew_id, idea, plan, project_name
    )

    return {
        "followed_through": True,
        "response": plan,
        "work_done": work_summary,
        "project_name": project_name
    }
