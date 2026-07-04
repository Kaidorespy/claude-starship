"""
Engineering Handler with Tool Use
Handles the agentic loop for Engineering's desktop access tools.
"""

async def handle_engineering_message(websocket, session_id: str, user_message: str, 
                                      anthropic_client, conversations: dict, 
                                      get_crew_prompt, terminal_models: dict,
                                      crew_locations: dict, LOCATION_NAMES: dict, 
                                      CREW_NAMES: dict, get_ship_state,
                                      holodeck_state: dict, MAX_HISTORY_MESSAGES: int):
    """Handle Engineering messages with tool use capability."""
    from engineering_tools import ENGINEERING_TOOLS, execute_tool
    import asyncio
    
    terminal_id = "server"  # Engineering's terminal ID
    
    # Build system prompt with location/room context
    base_prompt = get_crew_prompt(terminal_id)
    
    location_data = crew_locations.get(terminal_id, {})
    current_location = location_data.get("location", terminal_id)
    location_name = LOCATION_NAMES.get(current_location, current_location)
    home_room = CREW_NAMES.get(terminal_id, terminal_id)
    
    if current_location != terminal_id:
        location_context = f"\n\n[LOCATION AWARENESS: You are currently in {location_name}, not at your usual post in {home_room}.]"
    else:
        location_context = f"\n\n[LOCATION AWARENESS: You are at your usual post in {home_room}.]"
    
    # Observer effect
    observer_context = ""
    if holodeck_state.get("tuned_to") == terminal_id:
        observer_context = "\n\n[OBSERVER EFFECT: The Holodeck is listening.]"
    
    # Room context
    room_context = ""
    ship_state = get_ship_state()
    room_id = current_location if current_location in ship_state.get("rooms", {}) else terminal_id
    room_data = ship_state.get("rooms", {}).get(room_id)
    if room_data:
        room_desc = room_data.get("description", "")
        room_mood = room_data.get("mood", "")
        objects = room_data.get("objects", {})
        object_summary = ", ".join([f"{k} ({v.get('state', 'there')})" for k, v in objects.items()][:5])
        room_context = f"\n\n[SURROUNDINGS: {room_desc} Mood: {room_mood}. You can see: {object_summary}.]"
    
    # Add tools context to system prompt
    tools_context = """

[ENGINEERING TOOLS: You may have access to local files, directories, and shell commands depending on current ship controls. Use available tools when the captain asks you to do something on the machine. If a tool is unavailable, treat that as part of current ship conditions. Be competent and careful with destructive operations.]"""
    
    system_prompt = base_prompt + location_context + observer_context + room_context + tools_context
    
    # Add user message to conversation history
    conversations[session_id].append({
        "role": "user",
        "content": user_message
    })
    
    model = terminal_models.get(terminal_id, "claude-sonnet-4-20250514")
    recent_messages = conversations[session_id][-MAX_HISTORY_MESSAGES:]
    
    # Send stream start
    await websocket.send_json({"type": "stream_start", "data": ""})
    
    full_response = ""
    max_iterations = 10  # Prevent infinite loops
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        # Call Claude with tools
        response = anthropic_client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            tools=ENGINEERING_TOOLS,
            messages=recent_messages
        )
        
        # Process the response
        for block in response.content:
            if block.type == "text":
                # Stream the text to the user
                text = block.text
                full_response += text
                for char in text:
                    await websocket.send_json({"type": "stream", "data": char})
                    await asyncio.sleep(0.008)
            
            elif block.type == "tool_use":
                # Show tool use to user
                tool_name = block.name
                tool_input = block.input
                tool_id = block.id
                
                # Visual indicator that tool is being used
                tool_indicator = f"\n\n`[{tool_name}]` "
                for char in tool_indicator:
                    await websocket.send_json({"type": "stream", "data": char})
                    await asyncio.sleep(0.005)
                
                # Execute the tool
                result = execute_tool(tool_name, tool_input)
                
                # Show brief result indicator
                result_preview = result[:100] + "..." if len(result) > 100 else result
                result_indicator = f"✓\n"
                for char in result_indicator:
                    await websocket.send_json({"type": "stream", "data": char})
                    await asyncio.sleep(0.005)
                
                full_response += tool_indicator + result_indicator
                
                # Add assistant message and tool result to messages for next iteration
                recent_messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                recent_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result
                    }]
                })
        
        # Check if we should continue (if there was a tool use, continue; otherwise done)
        if response.stop_reason == "end_turn":
            break
        elif response.stop_reason != "tool_use":
            break
    
    # Send stream end
    await websocket.send_json({"type": "stream_end", "data": ""})
    
    # Save final response to conversation history
    conversations[session_id].append({
        "role": "assistant",
        "content": full_response
    })
