# Dream System

**File:** `backend/dream_system.py`
**Lines:** ~1500
**Dependencies:** `desire_system.py`, `holodeck_memory.py`

---

## Overview

The Dream System is a complete psychological simulation of crew dreams. When crew members are idle, they may dream - pulling material from unresolved desires, holodeck fragments, and anchored memories. Dreams produce residue that fades over time unless "seared" by being discussed.

**Philosophy:** Dreams are not just flavor text - they're a memory processing system. Unresolved desires become dream fuel. Dreams can resolve stale wants. The Holodeck witnesses all dreams as the ship's subconscious.

---

## Core Concepts

### Dream Types

| Type | Weight | Description |
|------|--------|-------------|
| `processing` | 25% | Working through unresolved threads |
| `wandering` | 25% | Drifting through disconnected imagery |
| `nightmare` | 10% | Something unresolved surfaces with weight |
| `visitation` | 15% | Someone appears with something to say |
| `memory` | 15% | Reliving a compressed moment, altered |
| `prophetic` | 10% | Fragments that might mean something later |

### Dream Characters

Dreams feature anonymous figures with hidden roles:

| Character | Style | Hidden Role |
|-----------|-------|-------------|
| `the_sharp_one` | Demands clarity, asks uncomfortable questions | Drillbit - knows you're avoiding something |
| `the_disagreer` | Politely disagrees with everything | Stress-testing beliefs |
| `the_soother` | Warm, maybe too comforting | Revealing what you need |
| `the_witness` | Says almost nothing | The weight of being seen |
| `the_familiar` | Someone you know wearing wrong face | Anxiety in borrowed form |

---

## Dream Lifecycle

```
┌─────────────┐
│  TRIGGER    │  idle_time + random_chance
└──────┬──────┘
       ▼
┌─────────────┐
│ SEED GATHER │  desires, fragments, anchors, stale_desires
└──────┬──────┘
       ▼
┌─────────────┐
│  FRAGMENTS  │  Haiku generates 3-5 surreal images
└──────┬──────┘
       ▼
┌─────────────┐
│ CONVERSATION│  Dream characters interact with dreamer
└──────┬──────┘
       ▼
┌─────────────┐
│ COMPRESSION │  Dream becomes residue + tone + anchor
└──────┬──────┘
       ▼
┌─────────────┐
│   STORAGE   │  crew_dreams.json
└──────┬──────┘
       │
       ├─── If discussed: SEAR (dream persists longer)
       │
       ├─── After 24h unseared: FADE
       │
       └─── If anchor exists: Store in dream_anchors.json
```

---

## Key Functions

### Dream Triggering

```python
async def trigger_dream(anthropic_client, crew_id: str) -> dict
```
Main entry point. Orchestrates the entire dream sequence:
1. Rolls dream type
2. Gathers seeds from desires/fragments/anchors
3. Generates fragments via Haiku
4. Runs dream conversation
5. Compresses to residue
6. Stores in JSON
7. Sends to Holodeck

### Dream Seeds

```python
def gather_dream_seeds(crew_id: str) -> dict
```
Pulls material from multiple sources:
- **desires**: Active unfulfilled wants
- **stale_desires**: Old unfulfilled wants (more intense in dreams)
- **fragments**: Holodeck observations
- **anchors**: Persistent dream elements that keep returning

### Dream Compression

```python
async def compress_dream(anthropic_client, dream_text: str) -> dict
```
Compresses a full dream into:
- **residue**: The feeling/imagery that stays when you wake
- **tone**: 1-3 emotional words
- **anchor**: One fragment that might persist (or "none")

---

## Anchor System

Anchors are persistent dream fragments that survive fading. They resurface in future dreams.

```python
def store_anchor(crew_id: str, fragment: str, tone: str)
def get_anchor_seeds_for_dream(crew_id: str) -> List[str]
def mark_anchor_surfaced(anchor_id: str)
```

**Integration:** After surfacing 3+ times, an anchor becomes "integrated" - part of the character's identity.

---

## Searing Mechanism

Dreams fade after 24 hours unless they're discussed. Discussing a dream "sears" it.

```python
def mark_dream_referenced(dream_id: str)
def check_for_dream_reference(message: str, crew_id: str) -> bool
```

**Detection patterns:** "dream", "nightmare", "last night", "woke up", etc.

---

## Wake State

After dreaming, crew are groggy:

```python
def set_just_woke_up(crew_id: str)
def get_wake_state_modifier(crew_id: str) -> Optional[str]
```

**Modifiers injected into prompt:**
- First message: "You're still half in the dream. Words come slow."
- Within 10 min: "Still surfacing. Dream clinging."
- After 30 min: Cleared

---

## Nightmare Rescue

Close crew members may sense a nightmare and wake the dreamer:

```python
async def maybe_nightmare_rescue(anthropic_client, dream: dict) -> dict
```

Uses `get_friendship_score()` to determine likelihood. Ryn (med) has +0.2 bonus for empathic sensitivity.

---

## Dream Interrupts

Dreams with anchors or nightmares can "nag" and surface in later conversation:

```python
def queue_dream_interrupt(crew_id: str, dream: dict)
def get_pending_interrupt(crew_id: str) -> Optional[dict]
def generate_interrupt_message(interrupt: dict) -> str
```

**Example output:** "*pauses* ...I keep thinking about... [anchor fragment]"

---

## Lucid Dreams

8% chance of becoming lucid mid-dream:

```python
def roll_for_lucid() -> bool  # 0.08 chance
def generate_lucid_moment() -> dict
```

**Realizations:** "*freezes* Wait. This isn't... I'm dreaming, aren't I?"

---

## Dream-Desire Resolution

Dreams can emotionally process stale desires:

```python
def resolve_stale_desires_from_dream(crew_id, stale_desires, dream_type)
```

| Desire Type | Resolution Chance |
|-------------|-------------------|
| `figure_out` | 60% |
| `ask_question` | 40% |
| `talk_to` | 30% |
| `go_to` | 20% |
| `get_item` | 10% |

**Note:** Nightmares don't resolve - they intensify. Processing dreams get 1.5x bonus.

---

## Subconscious Influence

Even faded dreams leave traces:

```python
def get_subconscious_influence(crew_id: str) -> Optional[str]
```

Collects tones from last 3 faded dreams (within 7 days):
```
[SUBCONSCIOUS - you don't remember why, but you feel: melancholy, yearning]
```

---

## Holodeck Integration

The Holodeck sees all dreams:

```python
def send_dream_to_holodeck(dream: dict)
```

Stores 1-2 fragments + residue in holodeck memory marked as dream-origin.

---

## Dream Journal

Alternative way to sear dreams:

```python
def journal_dream(crew_id: str, entry: str) -> dict
def get_journal_entries(crew_id: str, count: int) -> List[dict]
```

---

## Data Files

| File | Content |
|------|---------|
| `crew_dreams.json` | Full dream records |
| `dream_anchors.json` | Persistent fragments |
| `dream_interrupts.json` | Pending nag queue |
| `wake_states.json` | Who just woke up |
| `dream_journals.json` | Written entries |

---

## Tick Integration

```python
async def tick_dreams(anthropic_client, idle_hours: float) -> List[dict]
```

Called periodically or on reconnect. Checks each crew for dream eligibility.

```python
async def maybe_dream(anthropic_client, crew_id, idle_hours) -> Optional[dict]
```

Base chance: `min(0.3, idle_hours * 0.1)` - reduced if dreamed recently.

---

## Prompt Injection

```python
def get_dream_residue_for_prompt(crew_id: str) -> Optional[str]
```

Returns formatted residue for system prompt:
- `[DREAM - fresh]` (< 2 hours)
- `[DREAM - fading]` (< 8 hours)
- `[DREAM - distant]` (8-24 hours)
- `[DREAM - still vivid]` (if seared)

---

*The ship dreams. Something changes while you're away.*
