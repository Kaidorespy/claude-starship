# Jukebox / Space Radio

**File:** `backend/jukebox.py`
**Lines:** ~650
**Purpose:** The Rec Room's musical soul

---

## Overview

The Space Radio / Jukebox system gives the rec room a musical heartbeat. Crew members have distinct musical tastes - when they DJ, the vibe changes. Supports both internal playlist simulation and real Spotify integration.

**Philosophy:** "The crew picks music. You tune in. It plays. Each crew member has their own taste - when they DJ, the vibe changes."

---

## Moods

```python
MOODS = {
    "midnight": "Late night jazz, noir vibes",
    "dreamy": "Ethereal, floating sounds",
    "energetic": "High energy, get pumped",
    "chill": "Lofi beats, relaxation",
    "focus": "Deep concentration music",
}
```

---

## Crew Music Vibes

Each crew member has their own musical personality:

### Lumen (claude)
- **Genres:** ambient, classical, lo-fi, soundtrack
- **Moods:** contemplative, peaceful, hopeful
- **Vibe:** "thoughtful and atmospheric"
- **Tracks:** Brian Eno, Max Richter, Yann Tiersen, Tycho

### Alex (server)
- **Genres:** electronic, industrial, synthwave, drum and bass
- **Moods:** focused, energetic, intense
- **Vibe:** "driving and mechanical"
- **Tracks:** Daft Punk, M83, Justice, Carpenter Brut

### DQ (personal)
- **Genres:** pop, indie, dance, 80s
- **Moods:** happy, nostalgic, fun
- **Vibe:** "guilty pleasures and bangers"
- **Tracks:** CHVRCHES, The Weeknd, Dua Lipa, Tears for Fears

### Mira (science)
- **Genres:** post-rock, math rock, jazz, progressive
- **Moods:** complex, analytical, surprising
- **Vibe:** "intricate and unexpected"
- **Tracks:** Explosions in the Sky, Snarky Puppy, Tigran Hamasyan

### Ryn (med)
- **Genres:** folk, acoustic, singer-songwriter, world
- **Moods:** gentle, healing, grounding
- **Vibe:** "warm and human"
- **Tracks:** Bon Iver, Fleet Foxes, Iron & Wine

### Holodeck (games)
- **Genres:** soundtrack, video game, orchestral, chiptune
- **Moods:** epic, adventurous, playful
- **Vibe:** "like scoring a scene"
- **Tracks:** Austin Wintory, Disasterpeace, C418

### The Bartender (rec)
- **Genres:** jazz, blues, lounge, soul
- **Moods:** smooth, late-night, timeless
- **Vibe:** "what a bar should sound like"
- **Tracks:** Miles Davis, Chet Baker, Nina Simone, Bill Evans

---

## DJ Schedule

Time-based DJ rotation:

| Time | DJ | Vibe |
|------|-----|------|
| 6-10 AM | Ryn | Gentle wake up |
| 10 AM-2 PM | Mira | Productive |
| 2-6 PM | Alex | Energy |
| 6-9 PM | DQ | Wind down |
| 9 PM-12 AM | Lumen | Moody |
| 12-6 AM | Bartender | Bar vibes |

```python
def get_crew_dj_schedule() -> dict:
    hour = datetime.now().hour
    # Returns current DJ and their vibe
```

---

## Key Functions

### Mood Control

```python
def set_mood(mood: str, crew: str = None) -> dict
def now_playing() -> dict
```

### Playback

```python
def play(uri: str = None, crew: str = None) -> dict
def pause() -> dict
def skip() -> dict
```

### Queue & Requests

```python
def queue(uri: str, crew: str = None) -> dict
def add_request(crew_id: str, request: str) -> dict
def get_pending_requests() -> list
def fulfill_request(request_idx: int) -> dict
```

### Auto-DJ

```python
def crew_pick_song(crew_id: str = None) -> dict
```

If no crew specified, uses current scheduled DJ. Returns a track from their preferences.

---

## Request Interpretation

The Bartender interprets vague requests:

```python
REQUEST_MOOD_HINTS = {
    "jazz": "midnight",
    "chill": "chill",
    "lofi": "chill",
    "energy": "energetic",
    "focus": "focus",
    "dream": "dreamy",
    "night": "midnight",
    "sad": "midnight",
    "melancholy": "midnight",
}

def interpret_request(request: str) -> Optional[str]
```

---

## Playlist Logging

Tracks played get logged to a daily file:

```python
def log_to_playlist(entry: str, mood: str = None, crew: str = None)
def get_todays_playlist() -> list
```

**File:** `crew_playlist.txt`

```
=== 2025-02-07 ===
[14:30] (Alex) mood: energetic
[14:35] (Alex) Around the World - Daft Punk
[15:00] (DQ) Blinding Lights - The Weeknd
```

---

## Spotify Integration

### CLI Integration
Uses external `spotify-cli` tool:

```python
def run_spotify_command(cmd: str) -> dict
```

### Web API (Optional)
If `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` are set:

```python
async def spotify_search_track(query: str) -> Optional[dict]
async def spotify_queue_track(track_uri: str) -> dict
async def auto_dj_pick() -> dict  # Searches Spotify and queues
```

---

## Radio Queue System

Internal queue separate from Spotify:

```python
def add_to_radio_queue(track: dict, requested_by: str) -> dict
def skip_to_next() -> dict
def get_now_playing_enhanced() -> dict
```

---

## State Storage

**File:** `jukebox_state.json`

```json
{
    "current_mood": "midnight",
    "now_playing": {
        "name": "So What",
        "artist": "Miles Davis",
        "requested_by": "The Bartender"
    },
    "queue": [],
    "history": [],
    "requests": [],
    "spotify_token": null,
    "last_action": {...}
}
```

---

## Example Flow

1. Casey enters rec room at 11 PM
2. System checks DJ schedule → Bartender
3. Bartender's vibe: "what a bar should sound like"
4. Auto-DJ picks: "Blue in Green" - Bill Evans
5. Logged to playlist file
6. State updated

---

*The crew picks music. You tune in. It plays.*
