# Crew Cabins Feature

## Status: IMPLEMENTED

### What's Built

**Frontend**

- `frontend/index.html`
  - Crew cabins panel in captain's quarters sidebar (5 crew cards)
  - Notes history panel showing recent notes left

- `frontend/css/themes.css`
  - `.cabin-card` with away/home/active states
  - Per-crew color indicators
  - Note and reflection output styling
  - Notes history panel styling

- `frontend/js/terminals.js`
  - `initCrewCabins()` - setup, click handlers, polling
  - `updateCabinStates()` - polls `/crew/locations` every 30s
  - `openCabin(crewId)` - handles cabin visits
  - `exitCabin()` - returns to your quarters
  - `leaveCabinNote()` - explicit note (use `/note` prefix)
  - `leaveCabinReflection()` - ephemeral thoughts (default)
  - `loadNoteHistory()` - populates notes panel
  - Click active cabin to exit
  - Walkie slots track `cabinVisit` for intimate context

**Backend**

- `backend/server.py`
  - `get_cabin_notes_for_crew()` - get unread notes
  - `mark_cabin_notes_read_internal()` - auto-mark after crew responds
  - `get_cabin_reflections_for_crew()` - get unsensed reflections
  - `mark_cabin_reflections_sensed_internal()` - auto-mark after crew responds
  - `POST /cabin/{crew_id}/note` - leave explicit note
  - `POST /cabin/{crew_id}/reflection` - leave ephemeral thought
  - `GET /cabin/{crew_id}/notes` - get cabin notes
  - `GET /cabin/notes/all` - Casey's note history
  - `POST /cabin/{crew_id}/notes/mark-read` - manual mark read
  - Cabin visit context in system prompt for intimate conversations

---

## How It Works

### Cabin Cards (Quarters View)
1. Go to Quarters room
2. Left sidebar shows "CREW QUARTERS" panel
3. Each card shows crew member name + status
4. **Home** (in quarters): card is bright, pulsing indicator
5. **Away**: card is dimmed, shows where they are

### Empty Cabin Visit
1. Click a dimmed cabin card
2. Terminal shows cabin description
3. Placeholder: "think aloud... or /note to leave a message"
4. **Type normally** → reflection (ephemeral, sensed later)
5. **Type `/note X`** → explicit note (found on pillow)
6. Click cabin card again to exit

### Occupied Cabin Visit ("A Moment")
1. Click a bright cabin card
2. Opens walkie channel to them
3. System prompt includes intimate context:
   - Off-duty, private space
   - Softer, more vulnerable version of them
   - Not a status report - a personal visit

### Notes & Reflections

**Notes** (explicit, `/note` prefix):
- Stored in cabin object
- Crew "finds" note in their cabin
- Appears in system prompt: "You found a note from Casey..."
- Marked as read after crew responds
- Shown in Casey's "NOTES LEFT" history panel

**Reflections** (default, ephemeral):
- Stored in cabin object (max 3, older ones fade)
- Crew "senses" you were there
- More atmospheric prompt: "Your cabin feels different... warm..."
- Marked as sensed after crew responds
- Not shown in history (they're meant to be fleeting)

---

## Files Modified

- `frontend/index.html` - cabin cards HTML, notes history panel
- `frontend/css/themes.css` - all cabin styling
- `frontend/js/terminals.js` - cabin JS logic, walkie updates
- `backend/server.py` - cabin endpoints, prompt modifiers

---

## Usage Examples

**Leave a note:**
```
> /note thinking of you today
*You leave a note on Alex's pillow.*
```

**Leave a reflection:**
```
> I wonder if she knows how much this place means to me
*Your words hang in the air of Mira's empty cabin...*
*Maybe they'll sense you were here.*
```

**Visit someone home:**
- Click their bright cabin card
- Walkie opens with intimate context
- They respond as their off-duty self

---

## Data Storage

Notes and reflections are stored in `ship_state.json`:

```json
{
  "rooms": {
    "quarters": {
      "objects": {
        "alex_cabin": {
          "notes": [
            {"text": "...", "from": "casey", "timestamp": "...", "read": false}
          ],
          "reflections": [
            {"thought": "...", "timestamp": "...", "sensed": false}
          ],
          "has_unread_note": true,
          "has_unsensed_reflection": true
        }
      }
    }
  }
}
```
