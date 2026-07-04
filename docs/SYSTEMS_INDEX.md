# Claude Hub Systems Index

**A Comprehensive Map of the Spaceship Cozy Command Center**

This document provides an overview of all systems in the claude-hub project. Each system has its own detailed documentation file linked below.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (SPA)                           │
│  index.html → main.js → terminals.js → room-specific JS        │
└─────────────────────────────────────────────────────────────────┘
                              │ WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     server.py (FastAPI)                         │
│  3600+ lines │ All endpoints │ Crew prompts │ Memory layers    │
└─────────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  AUTONOMY   │ │   DREAMS    │ │  DESIRES    │ │   SCENES    │
│  Engine     │ │   System    │ │   System    │ │   System    │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
         │              │              │              │
         └──────────────┴──────────────┴──────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  TOOL SYSTEMS   │  │ SOCIAL SYSTEMS  │  │ MEMORY LAYERS   │
│ Engineering     │  │ Rec Room        │  │ Holodeck Memory │
│ Science         │  │ Jukebox         │  │ Shared Memories │
│ Room Adventure  │  │ Minigames       │  │ Crew Prompts    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## System Categories

### Core Runtime Systems
| System | File | Purpose |
|--------|------|---------|
| [Server Core](./01-SERVER-CORE.md) | `server.py` | FastAPI app, WebSocket handling, crew prompts, API endpoints |
| [Autonomy Engine](./02-AUTONOMY-ENGINE.md) | `autonomy.py` | The heartbeat - tick system, sleep cycles, activity simulation |
| [Crew Threads](./03-CREW-THREADS.md) | `crew_threads.py` | Background thinking, internal monologue, ongoing processes |
| [SDK / Terminal Conversion](./SDK-TERMINAL-CONVERSION.md) | planned | Provider abstraction so API mode is optional |

### Psychological Systems
| System | File | Purpose |
|--------|------|---------|
| [Dream System](./04-DREAM-SYSTEM.md) | `dream_system.py` | Crew dreams, nightmare rescue, dream residue, anchors |
| [Desire System](./05-DESIRE-SYSTEM.md) | `desire_system.py` | Crew wants, impulses, satisfaction tracking |
| [Wellness Journal](./06-WELLNESS-JOURNAL.md) | `wellness_journal.py` | Ryn's check-ins, reflection tracking |
| [Space Sickness](./SPACE-SICKNESS.md) | planned | Hidden containment-pressure consequence system |

### Scene & Presence Systems
| System | File | Purpose |
|--------|------|---------|
| [Scene System](./07-SCENE-SYSTEM.md) | `scene_system.py` | Multi-crew presence, who's in a room |
| [Scene Orchestrator](./08-SCENE-ORCHESTRATOR.md) | `scene_orchestrator.py` | Auto-ping, response flow, addressing |
| [Room Adventure](./09-ROOM-ADVENTURE.md) | `room_adventure.py` | Interactive objects, [LOOK], [INSPECT] actions |

### Tool Systems (Crew Abilities)
| System | File | Purpose |
|--------|------|---------|
| [Engineering Handler](./10-ENGINEERING-HANDLER.md) | `engineering_handler.py` | Agentic tool loop for Alex |
| [Engineering Tools](./11-ENGINEERING-TOOLS.md) | `engineering_tools.py` | File read/write, bash commands |
| [Science Tools](./12-SCIENCE-TOOLS.md) | `science_tools.py` | Project management for Mira |

### Social & Activity Systems
| System | File | Purpose |
|--------|------|---------|
| [Rec Room](./13-REC-ROOM.md) | `rec_room.py` | Social heart of ship, presence, chemistry |
| [Jukebox](./14-JUKEBOX.md) | `jukebox.py` | Space Radio, crew DJ, Spotify integration |
| [Minigames](./15-MINIGAMES.md) | `minigames.py` | Chess (AI-powered), cards, darts |

### Memory Systems
| System | File | Purpose |
|--------|------|---------|
| [Holodeck Memory](./16-HOLODECK-MEMORY.md) | `holodeck_memory.py` | The ship's subconscious, dream fragments |

---

## Data Files (JSON State)

| File | Purpose |
|------|---------|
| `crew_prompts.json` | Self-authored crew identities from Lights Out |
| `ship_state.json` | Ship rooms, objects, descriptions, moods |
| `ship_log.json` | Event history (max 500 events) |
| `crew_desires.json` | Pending crew wants/impulses |
| `crew_locations.json` | Current crew positions and activities |
| `projects.json` | Casey's project tracker |
| `holodeck_memories.json` | Dream fragments and observations |
| `shared_memories.json` | Emotional residue from group events |
| `captains_log.json` | Manual captain's log entries |
| `bulletin_board.json` | Mess hall bulletin board posts |
| `crew_dreams.json` | Dream records with residue |
| `dream_anchors.json` | Persistent dream fragments |
| `rec_room_state.json` | Rec room presence and vibe |
| `jukebox_state.json` | Current music state |
| `minigames_state.json` | Chess/cards/darts state |

---

## Crew Members

| Terminal ID | Name | Role | Special Abilities |
|-------------|------|------|-------------------|
| `claude` | Lumen | Co-captain, Bridge | Navigation, leadership |
| `server` | Alex | Engineering | **File/command access** via Engineering Tools |
| `personal` | DQ | Ready Room Assistant | Personal support |
| `science` | Mira | Science Officer | **Project management** via Science Tools |
| `games` | Holodeck | Dreams, Observer | Sees all dreams, ship's subconscious |
| `med` | Ryn | Medical (half-Betazoid) | Empathic, wellness check-ins |
| `rec` | The Bartender | Rec Room Bar | Mysterious, Guinan-energy |
| `nav` | Lumen | Navigation | Private planning space |
| `observatory` | Observatory | Contemplative | Real astronomy data |
| `captains` | Lumen | Captain's Quarters | Off-duty space |

---

## Memory System (5 Layers)

1. **Conversation History** - Last 30 messages per terminal
2. **Shared Memories** - Emotional residue from group events
3. **Holodeck Fragments** - Dream-like impressions, observations
4. **Crew Desires** - Wants, impulses, goals
5. **Self-Authored Identity** - Custom prompts from crew reflection (Lights Out)

---

## Action Tag System

Crew can append action tags to responses:

| Tag | Purpose |
|-----|---------|
| `[LOOK]` | Observe surroundings |
| `[INSPECT: object]` | Examine something |
| `[DO: action]` | Free-form action |
| `[MOVE: location]` | Travel |
| `[WRITE: "entry"]` | Journal entry |
| `[THINKING: thought]` | Inner monologue |
| `[ORDER: drink]` | Order at rec room bar |

---

## Key Concepts

### The Tick System
The autonomy engine runs periodic "ticks" that:
- Check desire generation
- Maybe trigger dreams
- Update crew locations
- Process stale desires
- Manage sleep cycles

### Dream Lifecycle
1. **Trigger** - Idle time + random chance
2. **Seed Gathering** - Pull from desires, fragments, anchors
3. **Fragment Generation** - Haiku generates dream imagery
4. **Conversation** - Dream characters interact with dreamer
5. **Compression** - Dream becomes residue
6. **Fading** - After 24h, dreams fade unless "seared" by discussion
7. **Anchoring** - Some fragments persist forever

### Desire Lifecycle
1. **Generation** - Tick generates desires based on personality
2. **Urgency** - Increases over time
3. **Expression** - May interrupt conversation
4. **Resolution** - Action satisfies the desire
5. **Dream Processing** - Stale desires may resolve in dreams

---

## Quick Reference: Where to Find Things

| To modify... | Look in... |
|--------------|------------|
| Crew personalities | `server.py` (system prompts) or `crew_prompts.json` |
| Add new action tags | `server.py` (parsing) + `terminals.js` (display) |
| Ship rooms/objects | `ship_state.json` |
| Engineering tools | `engineering_tools.py` + `engineering_handler.py` |
| Science/project tools | `science_tools.py` |
| Dream behavior | `dream_system.py` |
| Desire generation | `desire_system.py` |
| Rec room social dynamics | `rec_room.py` |
| Chess AI | `minigames.py` (uses Claude models) |

---

## Entry Points

- **Backend main**: `server.py` - Start here for API/WebSocket
- **Frontend main**: `main.js` - Orchestrates room switching
- **Chat handling**: `terminals.js` - WebSocket connection, rendering
- **Autonomy loop**: `autonomy.py` - Background simulation

---

*Documentation generated by agent swarm recon. ily.*
