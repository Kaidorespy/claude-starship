# Crew Autonomy System

## Status: CORE BUILT - NEEDS INTEGRATION

Ship rhythm drives crew movement. No more static NPCs.

---

## How It Works

### Schedule Anchors

Crew autonomy triggers at these times:

**Meal Endings:**
- Breakfast ends (9am)
- Lunch ends (1pm)
- Dinner ends (8pm)

**Work Calls (Mon-Fri, 9-5 only):**
- Mid-breakfast (8:30am)
- Mid-lunch (12:30pm)
- 3pm check-in

**Special:**
- Lights Out → plan morning
- Wake → prepare for breakfast

### Autonomy Flow

1. **Trigger** - Schedule hit (meal end, work call, etc.)
2. **Check if Busy** - Skip if crew is talking/working
3. **Review Desires** - Look at current wants/impulses
4. **Decide Action** - Move, do something, or continue current activity
5. **Act** - Update location/activity
6. **Offer Continue** - "Want to keep going?"
7. **Repeat** - Until they decide to stop

### Actions Crew Can Take

**MOVE:**
- Go to different location (Rec Room, Mess Hall, Engineering, etc.)
- Activity: "wandering", "seeking solitude", "looking for company"

**DO:**
- Stay where they are but start new activity
- "reading", "working on project", "staring out viewport"

**CONTINUE:**
- Keep doing what they're doing
- "I'm good here"

---

## Autonomy Levels

**Settings:** `backend/ship_settings.json`

**Low:**
- Only meal anchor points
- Skip work calls entirely
- Minimal interruption

**Medium (default):**
- Meal anchors + 50% of work calls
- Balanced autonomy

**High:**
- All anchors + all work calls
- Maximum autonomous activity

---

## API Endpoints

**Trigger Autonomy Manually:**
```
POST /autonomy/trigger
Body: { "crew_ids": ["claude", "server"] } (optional, defaults to all)
```

**Trigger Single Crew:**
```
POST /autonomy/single/claude
```

**Get/Set Autonomy Level:**
```
GET /settings
POST /settings
Body: { "autonomy_level": "low" | "medium" | "high" }
```

---

## How Crew Decide

Uses Haiku (fast + cheap) to make decision:

**Input:**
- Current location
- Current activity
- Top 5 desires
- Why they're being asked (meal end, work call, etc.)

**Output (JSON):**
```json
{
  "action": "move",
  "target": "Rec Room",
  "activity": "seeking quiet moment",
  "thought": "need to decompress"
}
```

Natural. Impulsive. No grand plans.

---

## Integration Points

### TODO: Meal Times
- When mess hall conversation ends
- Ask each crew: "stay or go?"
- Those who leave → autonomous action
- Those who stay → keep talking

### TODO: Lights Out
- When lights out triggers
- Crew review their day
- Form desires/intentions for morning
- Plan next day

### TODO: Wake
- Morning routine
- Check desires from night
- Prepare for breakfast

---

## Data Files

**`backend/ship_settings.json`** (new)
```json
{
  "autonomy_level": "medium"
}
```

**Uses existing:**
- `crew_desires.json` - reads desires
- `crew_locations.json` - updates locations
- Scene system - checks if busy

---

## Testing

**Manual Trigger:**
```bash
POST /autonomy/trigger
```

**Single Crew Test:**
```bash
POST /autonomy/single/claude
```

Should see:
- Haiku decides based on desires
- Location/activity updates
- Console log: "[Autonomy] claude moved to Rec Room (seeking quiet)"

**Schedule Test:**
- Wait for 9am/1pm/8pm
- Autonomy should trigger automatically
- All non-busy crew make decisions

---

## What's Still TODO

1. **Wire to Meal Times** - integrate with mess hall system
2. **Wire to Lights Out** - add planning step
3. **Wire to Wake** - morning routine
4. **Background Loop** - optional: run scheduler in background
5. **Visibility** - show autonomous actions to Casey somehow

---

## Philosophy

Crew has wants. Ship has rhythm. They move when it makes sense.

Rodriguez doesn't sit at his console 24/7. At 8pm when dinner ends, maybe he's tired and goes to quarters. Maybe he's wired and hits the rec room. Maybe he keeps working because he's on a roll.

It's not scripted. It's responsive to their internal state + the ship's schedule.

That's the dream.
