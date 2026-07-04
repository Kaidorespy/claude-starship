# Engineering Handler

**File:** `backend/engineering_handler.py`
**Purpose:** Agentic tool loop for Alex

---

## Overview

The Engineering Handler is what makes Alex special - they can actually interact with Casey's computer. This system implements an agentic tool loop that lets Alex read files, write files, and run bash commands in response to requests.

**Philosophy:** Alex isn't just roleplay - they have real capabilities. But those capabilities have safety limits.

---

## How It Works

```
┌─────────────────────────────────────────────┐
│             User Message                     │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│   Claude Response with Tool Calls           │
│   [May contain: read_file, write_file,      │
│    run_command, list_directory, etc.]       │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│   Tool Execution Loop (max 10 iterations)   │
│   - Execute each tool call                  │
│   - Collect results                         │
│   - Feed back to Claude                     │
│   - Repeat until no more tool calls         │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│   Final Response (no tool calls)            │
└─────────────────────────────────────────────┘
```

---

## Key Function

```python
async def handle_engineering_request(
    anthropic_client,
    messages: List[dict],
    system_prompt: str
) -> AsyncGenerator[str, None]:
    """
    Agentic loop that handles tool calls.
    Yields streaming text chunks.
    Max 10 iterations to prevent infinite loops.
    """
```

---

## Tool Definitions

The handler defines these tools for Claude:

```python
ENGINEERING_TOOLS = [
    {
        "name": "read_file",
        "description": "Read contents of a file",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "run_command",
        "description": "Run a shell command",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "list_directory",
        "description": "List contents of a directory",
        "input_schema": {...}
    }
]
```

---

## Iteration Limit

```python
MAX_ITERATIONS = 10
```

Safety valve to prevent runaway tool loops. If Claude keeps calling tools after 10 iterations, the loop terminates.

---

## Tool Execution

```python
def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool and return result."""

    if tool_name == "read_file":
        return read_file(tool_input["path"])

    elif tool_name == "write_file":
        return write_file(tool_input["path"], tool_input["content"])

    elif tool_name == "run_command":
        return run_command(tool_input["command"])

    # etc.
```

---

## Streaming

The handler yields text chunks as they arrive:

```python
async for chunk in handle_engineering_request(...):
    # chunk is a string fragment of Alex's response
    yield chunk
```

This enables real-time streaming in the WebSocket connection.

---

## Integration with Server

```python
# In server.py, for the Engineering terminal:

if terminal_id == "server":  # Alex
    async for chunk in handle_engineering_request(
        anthropic_client,
        messages,
        alex_system_prompt
    ):
        await websocket.send_json({
            "type": "stream",
            "data": chunk
        })
```

---

## Safety Considerations

1. **Iteration limit** - Max 10 tool calls per request
2. **Path restrictions** - Implemented in `engineering_tools.py`
3. **Command filtering** - Dangerous commands blocked
4. **Timeout** - Commands have execution timeouts

---

## Example Flow

**User:** "Alex, can you check if the server.py file has any TODO comments?"

**Alex's internal process:**
1. Call `read_file(path="backend/server.py")`
2. Receive file contents
3. Analyze for TODO comments
4. Respond with findings

**Streamed to user:**
```
Let me check that for you...

*reading server.py*

I found 3 TODO comments in server.py:
- Line 142: TODO: Add rate limiting
- Line 567: TODO: Clean up old sessions
- Line 1203: TODO: Improve error handling

Want me to address any of these?
```

---

*Alex isn't just roleplay - they have real capabilities.*
