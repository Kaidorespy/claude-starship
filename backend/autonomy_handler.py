"""
AUTONOMY HANDLER
Crew makes decisions and acts on desires.
"""

import json
from typing import Dict, List
from datetime import datetime


async def crew_autonomous_action(
    crew_id: str,
    desires: List[Dict],
    reason: str,
    anthropic_client
) -> Dict:
    """
    Crew member reviews their desires and decides what to do.
    They might move, do an action, or decide to continue what they're doing.
    """
    from scene_system import get_crew_locations_data, update_crew_location
    from desire_system import mark_desire_acted_on

    # Get current state
    locations = get_crew_locations_data()
    crew_data = locations.get(crew_id, {})
    current_location = crew_data.get("location", crew_id)
    current_activity = crew_data.get("activity", "idle")

    # Build context for decision
    desires_text = "\n".join([
        f"- {d.get('reason', 'unknown')} (intensity: {d.get('intensity', 0.5)})"
        for d in desires[:5]  # Top 5
    ])

    prompt = f"""You are deciding what to do right now based on your current wants and impulses.

CURRENT STATE:
- Location: {current_location}
- Activity: {current_activity}
- Trigger: {reason}

YOUR DESIRES:
{desires_text}

DECISION NEEDED:
What do you want to do RIGHT NOW? You can:
1. MOVE to a different location (Bridge, Engineering, Science, Holodeck, Rec Room, Mess Hall, Medbay, Quarters, Captain's Quarters, Ready Room, Observatory, Corridor, Bathroom)
2. DO something where you are (action/activity)
3. CONTINUE what you're doing (stay put)

Respond with JSON:
{{
  "action": "move" | "do" | "continue",
  "target": "location name" (if move),
  "activity": "what you're doing" (if do or move),
  "thought": "quick inner thought about why"
}}

Be natural. Follow your impulses. You don't need a grand reason."""

    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-20250514",  # Fast for autonomy
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = response.content[0].text.strip()

        # Parse JSON
        import re
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if not json_match:
            return {"status": "no_action", "crew": crew_id, "reason": "invalid_response"}

        decision = json.loads(json_match.group())

        action_type = decision.get("action", "continue")

        if action_type == "move":
            target = decision.get("target", current_location)
            activity = decision.get("activity", "wandering")

            # Update location
            update_crew_location(crew_id, target, activity)

            # Mark most relevant desire as acted on
            if desires:
                mark_desire_acted_on(crew_id, desires[0]["id"])

            print(f"[Autonomy] {crew_id} moved to {target} ({activity})", flush=True)

            return {
                "status": "moved",
                "crew": crew_id,
                "from": current_location,
                "to": target,
                "activity": activity,
                "thought": decision.get("thought", "")
            }

        elif action_type == "do":
            activity = decision.get("activity", "doing something")

            # Update activity in current location
            update_crew_location(crew_id, current_location, activity)

            if desires:
                mark_desire_acted_on(crew_id, desires[0]["id"])

            print(f"[Autonomy] {crew_id} is now {activity}", flush=True)

            return {
                "status": "action",
                "crew": crew_id,
                "location": current_location,
                "activity": activity,
                "thought": decision.get("thought", "")
            }

        else:  # continue
            print(f"[Autonomy] {crew_id} continuing current activity", flush=True)

            return {
                "status": "continue",
                "crew": crew_id,
                "location": current_location,
                "activity": current_activity,
                "thought": decision.get("thought", "")
            }

    except Exception as e:
        print(f"[Autonomy] Error for {crew_id}: {e}", flush=True)
        return {"status": "error", "crew": crew_id, "error": str(e)}


async def offer_continue(crew_id: str, anthropic_client) -> bool:
    """
    After an autonomous action, ask crew if they want to continue acting.
    Returns True if they want to keep going.
    """
    from scene_system import get_crew_locations_data
    from desire_system import get_crew_desires

    locations = get_crew_locations_data()
    crew_data = locations.get(crew_id, {})
    current_location = crew_data.get("location", crew_id)
    current_activity = crew_data.get("activity", "idle")

    desires = get_crew_desires(crew_id)

    if not desires:
        return False  # No more desires, done

    prompt = f"""You just did something: {current_activity} at {current_location}.

You still have these wants:
{chr(10).join([f"- {d.get('reason', '')}" for d in desires[:3]])}

Do you want to keep acting on your desires, or settle down for now?

Respond with JSON:
{{"continue": true/false, "thought": "why"}}"""

    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-20250514",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = response.content[0].text.strip()
        import re
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            decision = json.loads(json_match.group())
            return decision.get("continue", False)

    except:
        pass

    return False  # Default: don't continue
