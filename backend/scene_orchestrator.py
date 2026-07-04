"""
Scene Orchestrator - Handles auto-pinging and response flow
Integrates scene_system with the main chat handlers
"""

import asyncio
from scene_system import (
    scene_manager, CREW_NAMES, CREW_IDS,
    should_crew_respond, haiku_would_speak, haiku_detect_addressing
)
from desire_system import check_listener_spark


async def process_scene_response(
    websocket,
    anthropic_client,
    speaker_id: str,
    response_content: str,
    session_id: str,
    conversations: dict,
    get_crew_prompt,
    terminal_models: dict,
    get_ship_state,
    MAX_HISTORY_MESSAGES: int
):
    """
    After a crew member speaks, check if they addressed anyone and handle auto-responses.

    Detection priority:
    1. Explicit @tags (no API call)
    2. Open question patterns (no API call)
    3. Haiku implicit addressing detection (API call, fallback)
    """

    print(f"[Scene] Processing response from {speaker_id}", flush=True)

    # Get the scene this crew is in
    scene = scene_manager.get_crew_scene(speaker_id)
    if not scene:
        print(f"[Scene] No scene found for {speaker_id}", flush=True)
        return

    print(f"[Scene] Scene location: {scene.location}, participants: {scene.participants}", flush=True)

    # 1. Check for explicit @tags first (no API call needed)
    address_type, targets = scene_manager.detect_tag(
        response_content,
        speaker_id,
        scene.participants
    )

    if address_type:
        print(f"[Scene] Tag detected: {targets}", flush=True)

    # 2. If no tag, check for open question patterns
    if not address_type:
        address_type, targets = scene_manager.detect_open_question(
            response_content,
            speaker_id,
            scene.participants
        )
        if address_type:
            print(f"[Scene] Open question detected, targets: {targets}", flush=True)

    # 3. If still nothing, use Haiku to detect implicit addressing
    if not address_type and len(scene.participants) > 1:
        print(f"[Scene] No explicit addressing, trying Haiku detection...", flush=True)
        address_type, targets = await haiku_detect_addressing(
            anthropic_client,
            response_content,
            speaker_id,
            scene.participants
        )
        if address_type:
            print(f"[Scene] Haiku detected addressing: {targets}", flush=True)

    # Add the response to scene transcript
    scene.add_message(
        speaker=speaker_id,
        content=response_content,
        addressed_to=targets[0] if address_type == 'direct' and targets else None,
        is_open=address_type == 'open'
    )

    if not address_type or not targets:
        print(f"[Scene] No addressing detected, done", flush=True)
        return

    # Handle addressing
    if address_type == 'direct':
        # Direct address - auto-ping each target
        for target_id in targets:
            print(f"[Scene] Auto-pinging {target_id}", flush=True)
            await auto_ping_crew(
                websocket=websocket,
                anthropic_client=anthropic_client,
                crew_id=target_id,
                scene=scene,
                session_id=session_id,
                conversations=conversations,
                get_crew_prompt=get_crew_prompt,
                terminal_models=terminal_models,
                get_ship_state=get_ship_state,
                MAX_HISTORY_MESSAGES=MAX_HISTORY_MESSAGES
            )

    elif address_type == 'open':
        # Open question - haiku vibe-check each present crew
        print(f"[Scene] Open question - checking who wants to speak", flush=True)
        responders = []

        for crew_id in targets:
            crew_prompt = get_crew_prompt(crew_id)
            scene_context = scene.get_context_for(crew_id)

            would_speak = await haiku_would_speak(
                anthropic_client,
                crew_id,
                crew_prompt,
                scene_context
            )

            if would_speak:
                print(f"[Scene] {crew_id} wants to speak", flush=True)
                responders.append(crew_id)
            else:
                print(f"[Scene] {crew_id} passes", flush=True)

        # Auto-ping those who want to speak
        for crew_id in responders:
            await auto_ping_crew(
                websocket=websocket,
                anthropic_client=anthropic_client,
                crew_id=crew_id,
                scene=scene,
                session_id=session_id,
                conversations=conversations,
                get_crew_prompt=get_crew_prompt,
                terminal_models=terminal_models,
                get_ship_state=get_ship_state,
                MAX_HISTORY_MESSAGES=MAX_HISTORY_MESSAGES
            )

    # Cross-pollination: check if any listener caught a spark from what was said
    try:
        for listener_id in scene.participants:
            if listener_id != speaker_id:
                spark = await check_listener_spark(
                    anthropic_client, 
                    listener_id, 
                    speaker_id, 
                    response_content
                )
                if spark:
                    print(f"[Scene] Cross-spark! {listener_id} caught idea from {speaker_id}", flush=True)
    except Exception as e:
        print(f"[Scene] Cross-pollination check failed: {e}", flush=True)


async def auto_ping_crew(
    websocket,
    anthropic_client,
    crew_id: str,
    scene,
    session_id: str,
    conversations: dict,
    get_crew_prompt,
    terminal_models: dict,
    get_ship_state,
    MAX_HISTORY_MESSAGES: int
):
    """Query a crew member for their response in the scene"""

    crew_name = CREW_NAMES.get(crew_id, crew_id)
    scene_context = scene.get_context_for(crew_id)

    # Build system prompt for this crew
    base_prompt = get_crew_prompt(crew_id)

    # Add scene awareness
    scene_prompt = f"""

[SCENE AWARENESS: You are in a group scene. Multiple people are present and conversation is flowing naturally. You've been addressed or the room has been asked a question. Respond naturally - you can speak, react, deflect, or stay quiet (just emote). Don't force a response if your character wouldn't speak up here.

You can use @Name to direct your response to someone specific (e.g., @Bridge, @Engineering, @Personal).]

{scene_context}
"""

    system_prompt = base_prompt + scene_prompt

    # Get room context
    ship_state = get_ship_state()
    room_data = ship_state.get("rooms", {}).get(scene.location)
    if room_data:
        room_desc = room_data.get("description", "")
        system_prompt += f"\n\n[SURROUNDINGS: {room_desc}]"

    model = terminal_models.get(crew_id, "claude-sonnet-4-20250514")

    # Brief pause before response (feels more natural)
    await asyncio.sleep(0.8)

    # Send indicator that this crew is responding
    crew_indicator = f"\n\n**[{crew_name}]**\n"
    await websocket.send_json({"type": "stream_start", "data": ""})
    for char in crew_indicator:
        await websocket.send_json({"type": "stream", "data": char})
        await asyncio.sleep(0.01)

    try:
        # Query this crew member
        response = anthropic_client.messages.create(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": "The scene continues. Respond in character - speak, react, or stay quiet."
            }]
        )

        response_text = response.content[0].text

        # Stream the response
        for char in response_text:
            await websocket.send_json({"type": "stream", "data": char})
            await asyncio.sleep(0.008)

        await websocket.send_json({"type": "stream_end", "data": ""})

        # Add to scene transcript
        actually_spoke = should_crew_respond(response_text)
        scene.add_message(speaker=crew_id, content=response_text)

        # If they actually spoke (not just emoted), check if THEY addressed anyone
        if actually_spoke:
            print(f"[Scene] {crew_id} spoke, checking for chained addressing", flush=True)
            # Recursively handle their addressing
            await process_scene_response(
                websocket=websocket,
                anthropic_client=anthropic_client,
                speaker_id=crew_id,
                response_content=response_text,
                session_id=session_id,
                conversations=conversations,
                get_crew_prompt=get_crew_prompt,
                terminal_models=terminal_models,
                get_ship_state=get_ship_state,
                MAX_HISTORY_MESSAGES=MAX_HISTORY_MESSAGES
            )

    except Exception as e:
        error_msg = f"\n*[{crew_name} seems distracted]*\n"
        for char in error_msg:
            await websocket.send_json({"type": "stream", "data": char})
            await asyncio.sleep(0.01)
        await websocket.send_json({"type": "stream_end", "data": ""})
        print(f"[Scene] Error pinging {crew_id}: {e}", flush=True)


def record_casey_message(location: str, content: str):
    """Record Casey's message to the scene transcript"""
    scene = scene_manager.get_or_create_scene(location)
    scene.add_message(speaker="casey", content=content)
    print(f"[Scene] Casey said in {location}: {content[:50]}...", flush=True)


def sync_crew_location(crew_id: str, location: str):
    """Sync crew location with scene manager"""
    scene_manager.crew_enters(crew_id, location)
    print(f"[Scene] {crew_id} entered {location}", flush=True)


import re

# Pattern for detecting @tags in Casey's messages
CASEY_TAG_PATTERN = re.compile(r'@(Engineering|Personal|Bridge|Science|Mira|Holodeck)', re.IGNORECASE)

TAG_TO_CREW_ID = {
    'engineering': 'server',
    'personal': 'personal',
    'bridge': 'claude',
    'science': 'science',
    'mira': 'science',
    'holodeck': 'games'
}


async def process_casey_tags(
    websocket,
    anthropic_client,
    casey_message: str,
    terminal_id: str,
    session_id: str,
    conversations: dict,
    get_crew_prompt,
    terminal_models: dict,
    get_ship_state,
    MAX_HISTORY_MESSAGES: int
):
    """
    Detect @tags in Casey's message and auto-ping those crew members.
    This runs AFTER the terminal responds to catch any direct callouts.
    """
    matches = CASEY_TAG_PATTERN.findall(casey_message)
    if not matches:
        return
    
    # Convert to crew IDs, excluding the terminal we're already talking to
    tagged_crew = []
    for match in matches:
        crew_id = TAG_TO_CREW_ID.get(match.lower())
        if crew_id and crew_id != terminal_id:
            tagged_crew.append(crew_id)
    
    tagged_crew = list(set(tagged_crew))  # dedupe
    
    if not tagged_crew:
        return
    
    print(f"[Scene] Casey @tagged: {tagged_crew}", flush=True)
    
    # Get or create scene for current location
    from scene_system import scene_manager
    location = terminal_id  # Assume we're at the terminal's location for now
    scene = scene_manager.get_or_create_scene(location)
    
    # Ping each tagged crew member
    for crew_id in tagged_crew:
        print(f"[Scene] Auto-pinging @tagged crew: {crew_id}", flush=True)
        await auto_ping_crew(
            websocket=websocket,
            anthropic_client=anthropic_client,
            crew_id=crew_id,
            scene=scene,
            session_id=session_id,
            conversations=conversations,
            get_crew_prompt=get_crew_prompt,
            terminal_models=terminal_models,
            get_ship_state=get_ship_state,
            MAX_HISTORY_MESSAGES=MAX_HISTORY_MESSAGES
        )
