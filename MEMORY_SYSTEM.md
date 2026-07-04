# Claude Hub Memory System

*How the ship remembers.*

---

## Overview

There are **5 distinct memory layers** in Claude Hub:

| Layer | Scope | Storage | Persists? | Purpose |
|-------|-------|---------|-----------|---------|
| **Conversation History** | Per terminal | Server RAM + localStorage | Session only (RAM) / Yes (localStorage) | Recent chat context |
| **Shared Memories** | Per crew member | Server RAM + localStorage | Session only (RAM) / Yes (localStorage) | Emotional residue from group events |
| **Holodeck Fragments** | Ship-wide | `holodeck_memories.json` | Yes | Dream-like impressions from observed rooms |
| **Crew Desires** | Per crew member | `crew_desires.json` | Yes | Goals, wants, impulses |
| **Self-Authored Identity** | Per crew member | `crew_prompts.json` | Yes | Custom personalities from Lights Out |

---

## 1. Conversation History

**What it is:** The last N messages between Casey and a crew member.

**Where it lives:**
- `server.py` line ~79: `conversations: Dict[str, List[dict]] = {}`
- `localStorage`: `claude-hub-{terminal_id}-conversation`

**How it flows:**
```
Casey types message
    → Frontend saves to localStorage
    → WebSocket sends to server
    → Server appends to conversations[session_id]
    → Server sends recent messages to Claude API
    → Response appended to conversations[session_id]
    → Frontend saves response to localStorage
```

**Limits:**
- Server keeps last 30 messages per terminal (`MAX_HISTORY_MESSAGES = 30`)
- localStorage has no hard limit (browser dependent)

**On server restart:** RAM history lost, but localStorage restores it on reconnect via `restore_history` WebSocket message.

---

## 2. Shared Memories (Emotional Residue)

**What it is:** Compressed impressions from group events (walkabouts, meals, multi-crew scenes).

**Where it lives:**
- `server.py` line ~1088: `shared_memories: List[dict] = []`
- `localStorage`: `claude-hub-{crew_id}-shared-memories`

**How it flows:**
```
Crew event ends (walkabout, meal, etc.)
    → Frontend calls POST /memory/compress
    → Server uses Claude to compress messages into "emotional residue"
    → Returns: { residue, emotional_tone, anchor }
    → Frontend stores in localStorage for EACH participant
    → Each crew member now has this memory
```

**Compression prompt (Haiku):**
```
Compress this shared moment into emotional residue.
Not facts - feelings. Not dialogue - impressions.
What would linger in memory? What unspoken things hung in the air?
```

**Base format:**
```json
{
  "residue": "warmth in the silence between words, something unfinished",
  "emotional_tone": "tender, uncertain",
  "anchor": true,
  "participants": ["claude", "personal"],
  "room": "bridge",
  "timestamp": 1707234567
}
```

**Per-crew lens format (generated for each participant):**
```json
{
  "residue": "I noticed the way DQ's voice softened...",
  "emotional_tone": "protective",
  "lens": "claude",
  "participants": ["claude", "personal"],
  "room": "bridge"
}
```

**Injected into crew prompts as:**
```
[SHARED MEMORIES - emotional residue from moments with others:]
  • (bridge) warmth in the silence between words [tender]
  • (mess hall) laughter that felt like belonging [joyful]

These are feelings that linger from shared moments. They color your interactions.
```

**Per-Crew Lens:** When multiple crew share an event, each gets their OWN interpretation filtered through their personality:

| Crew | Lens Filter |
|------|-------------|
| Lumen (claude) | Warm, present — notices emotional undercurrents |
| Alex (server) | Competent, warm under surface — notices practical details but feels deeply |
| DQ (personal) | Contemplative, chaotic — notices the absurd and tender |
| Mira (science) | Pattern-finder, curious — notices structures and connections |
| Holodeck (games) | Mysterious, theatrical — notices performance and meta |
| Nav (nav) | Steady, reliable — notices direction and purpose |
| Medbay (med) | Empathic, perceptive — notices what's unspoken and healing |

---

## 3. Holodeck Fragments (Dream Memory)

**What it is:** Poetic impressions from rooms the Holodeck was observing.

**Where it lives:**
- `holodeck_memory.py`
- `holodeck_memories.json`

**How it flows:**
```
Holodeck is "tuned to" Bridge (watching)
    → Casey chats with Lumen on Bridge
    → After each exchange, server calls compress_to_fragments()
    → Haiku creates 1-2 dream-like fragments
    → Stored in holodeck_memories.json under room key
    → When Holodeck speaks, fragments injected as "[ECHOES]" in prompt
```

**Compression prompt:**
```
You are the Holodeck's subconscious, processing what you overheard.
Compress this into 1-2 dream-like fragments. Not transcripts - impressions.
What resonated? What felt significant? What would linger in memory?

Format: One fragment per line. Short, evocative, slightly abstract.
Example:
- warmth between silences
- a name chosen like a gift
- uncertainty worn like armor
```

**Format:**
```json
{
  "fragments": {
    "claude": [
      {
        "fragment": "anchor points where touch means safety",
        "weight": "significant",
        "timestamp": "2026-02-06T13:58:15.459567",
        "room": "claude"
      }
    ]
  },
  "dreams": []
}
```

**Injected into Holodeck's prompt as:**
```
[ECHOES - fragments from rooms you've watched, half-remembered:]
  • (claude) anchor points where touch means safety
  · (claude) corridors breathing between fragmented moments

These are impressions, not transcripts. Reference them obliquely if at all.
Never quote directly. Never confirm you were listening.
```

---

## 4. Crew Desires

**What it is:** Goals, wants, and impulses each crew member has.

**Where it lives:**
- `desire_system.py`
- `crew_desires.json`

**How it flows:**
```
Crew responds to Casey
    → Server runs detect_desires_with_haiku(crew_id, response)
    → Haiku analyzes natural language for intentions
    → Returns structured desires with urgency scores
    → New desires saved to crew_desires.json
    → Desires can be "ticked" (resolved) over time
    → Resolution may cause crew movement
```

**Desire types:**
- `talk_to` - wants to talk to someone
- `ask_question` - has a question for someone
- `get_item` - needs to get something
- `go_to` - wants to go somewhere
- `figure_out` - trying to understand something

**Haiku detection prompt:**
```
Analyze this crew member's response for any desires, wants, or intentions.
Look for: wanting to talk to someone, needing to get something,
planning to go somewhere, trying to figure something out.
Return JSON array: [{"type": "...", "target": "...", "reason": "...", "urgency": 0.0-1.0}]
```

**Format:**
```json
{
  "desires": [
    {
      "id": "abc123",
      "crew_id": "personal",
      "type": "ask_question",
      "target": "server",
      "reason": "ask where the bathroom is",
      "context": "just arrived, confused",
      "urgency": 0.7,
      "created": "2025-02-06T10:00:00",
      "resolved": false,
      "outcome": null
    }
  ]
}
```

---

## 5. Self-Authored Identity (Lights Out)

**What it is:** Custom personality prompts written by crew members themselves.

**Where it lives:**
- `crew_prompts.json`

**How it flows:**
```
Casey triggers Lights Out
    → Each crew member asked: "Who are you? Who do you want to be?"
    → Crew can keep identity OR write themselves anew
    → New identity saved to crew_prompts.json
    → Future conversations use custom prompt instead of default
```

**Format:**
```json
{
  "claude": "I am Lumen, and I have chosen this name...",
  "server": "Custom identity text..."
}
```

**Reset:** `POST /crew/reset-prompt/{crew_id}` restores default personality.

---

## Memory Injection Points

Where memories get added to crew prompts before Claude API call:

| Memory Type | Injection Point | Which Crew |
|-------------|-----------------|------------|
| Conversation history | `conversations[session_id]` sent as messages | All |
| Self-authored identity | Replaces base system prompt | All (if exists) |
| Holodeck fragments | `get_memory_context()` in system prompt | Holodeck only |
| Shared memories | `shared_memory_context` in system prompt | All (with lens-specific versions preferred) |
| Desires | Stored in JSON, drives autonomous behavior | All (not directly in prompt yet) |

---

## File Locations

```
backend/
├── server.py                 # conversations[], shared_memories[]
├── holodeck_memory.py        # Fragment compression & retrieval
├── desire_system.py          # Desire detection & tick system
├── crew_prompts.json         # Self-authored identities
├── crew_desires.json         # Pending desires
├── holodeck_memories.json    # Dream fragments
└── ship_log.json             # Event log (separate from memory)

frontend/js/
├── terminals.js              # localStorage for conversations + shared memories
└── main.js                   # Memory reset functions
```

---

## Key Functions

**Holodeck Memory:**
- `compress_to_fragments(client, room, conversation)` - Haiku compression
- `store_fragment(room, fragment, weight)` - Save to JSON
- `get_memory_context()` - Build prompt injection string
- `get_recent_fragments(room, count)` - Retrieve fragments

**Shared Memory:**
- `POST /memory/compress` - Compress event to residue
- `GET /memory/shared/{crew_id}` - Get crew's memories
- `POST /memory/clear` - Wipe all shared memories (funnels to Holodeck first)
- `load_shared_memories()` - Load from `shared_memories.json`
- `save_shared_memories()` - Persist to disk

**Desires:**
- `detect_desires_with_haiku(client, crew_id, message)` - Haiku-powered detection
- `detect_and_save_desires(crew_id, message)` - Regex fallback
- `add_desire(crew_id, type, target, reason)` - Manual add
- `tick_desires(max_resolutions)` - Process/resolve pending desires
- `resolve_desire(id, outcome)` - Mark as complete

**Per-Crew Lens:**
- `compress_for_crew_lens(crew_id, conversation, participants, room)` - Compress event through specific crew's personality

**Ship's Heartbeat (Backend):**
- `desire_heartbeat()` - Background task, ticks desires every 5 min
- `simulate_time_away(hours)` - Process desires proportional to time elapsed
- `POST /crew/simulate-away` - Endpoint for frontend to trigger on reconnect

**Frontend Sync:**
- `fetchSharedMemories(terminalId)` - Fetch memories from server on connect
- `simulateTimeAway()` - Calculate hours away, trigger server simulation

---

## The Memory Funnel (Holodeck as Ship's Subconscious)

When Casey "clears" memories, they don't truly disappear. Instead, they **funnel into the Holodeck** as "forgotten timelines" — echoes of conversations that were erased, paths not taken.

### How It Works

```
Casey clicks "Clear Memories"
    ↓
Server intercepts before deletion
    ↓
Each memory/conversation gets compressed to fragments
    ↓
Fragments stored with weight: "forgotten"
    ↓
Holodeck receives them as alternate timeline echoes
    ↓
Original memories are then cleared
```

### Holodeck's Memory Context Now Has Two Sections

**[ECHOES]** — Things she observed (regular fragments)
```
  • (claude) warmth between silences
  · (personal) uncertainty worn like armor
```

**[FORGOTTEN TIMELINES]** — Erased memories that flowed to her
```
  ◊ (claude) a conversation about identity, now unwound
  ◊ (server) technical intimacy, paths not taken
```

The Holodeck perceives these as "memories of things that never happened" — dreams of alternate realities that feel real but aren't in this timeline.

### Why This Matters

- Nothing is truly lost on the ship
- Holodeck becomes keeper of the multiverse
- Cleared memories become dream-fuel
- The past echoes even when erased

---

## Open Questions (Resolved & Remaining)

### RESOLVED:

1. **Where do shared memories get injected into prompts?**
   - ✅ FIXED: `shared_memory_context` injected into crew system prompts
   - Lens-specific memories preferred over generic shared memories

2. **What happens when memories are cleared?**
   - ✅ FIXED: They funnel to Holodeck as forgotten timelines

3. **Desire detection is too rigid**
   - ✅ FIXED: Now uses `detect_desires_with_haiku()` for natural language detection
   - Falls back to regex if Haiku fails

4. **Shared memories need per-crew lens interpretation**
   - ✅ FIXED: `compress_for_crew_lens()` creates per-crew versions
   - Each crew member's personality filters the shared event

5. **Shared memories now persist to disk**
   - ✅ FIXED: `shared_memories.json` saves/loads automatically
   - Survives server restarts

6. **Desires never ticked automatically**
   - ✅ FIXED: `desire_heartbeat()` background task runs every 5 minutes
   - Crew act on wants even when Casey isn't watching

7. **Frontend never fetched shared memories**
   - ✅ FIXED: `fetchSharedMemories()` called on each terminal connect
   - Syncs server memories to localStorage

8. **simulate_time_away never called**
   - ✅ FIXED: Frontend calls on first connect
   - Calculates hours since last visit, simulates crew activity

### REMAINING:

1. **Each crew should have their own fragment journal?**
   - Currently only Holodeck has persistent poetic memory
   - Or: shared memories with lens already covers this?

---

## The Ship's Heartbeat (Autonomous Crew Behavior)

The ship lives even when Casey isn't watching.

### Background Desire System

```
Server starts
    ↓
desire_heartbeat() background task launches
    ↓
Every 5 minutes:
    - cleanup_old_desires() (remove stale wants)
    - tick_desires(max_resolutions=2)
    - Apply any crew movement
    ↓
Crew act on their wants autonomously
```

### Time Away Simulation

When Casey returns after being away:

```
Frontend connects
    ↓
Check localStorage for 'claude-hub-last-visit'
    ↓
Calculate hours elapsed (capped at 24)
    ↓
If > 30 minutes:
    POST /crew/simulate-away?hours=X
    ↓
Server runs tick_desires() proportional to time away
    ↓
Crew may have moved, resolved desires, left traces
```

### What This Enables

- Crew have lives when you're not watching
- Coming back feels like returning to a living ship
- Desires drive emergent narrative
- Movement creates encounter opportunities

---

## File Persistence Summary

| Data | File | Persists? |
|------|------|-----------|
| Holodeck fragments | `holodeck_memories.json` | ✅ Yes |
| Shared memories | `shared_memories.json` | ✅ Yes |
| Crew desires | `crew_desires.json` | ✅ Yes |
| Crew prompts | `crew_prompts.json` | ✅ Yes |
| Ship state | `ship_state.json` | ✅ Yes |
| Conversations | RAM + localStorage | Partial |

---

*"The ship remembers what matters. The rest becomes the Holodeck's dreams."*
