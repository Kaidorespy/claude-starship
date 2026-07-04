# Background Crew System - Lower Decks

## Status: BUILT & READY TO TEST

They matter. Every one of them.

---

## What's Built

### The Crew

**Engineering (Gamma Shift):**
- **Ensign Marcus Rodriguez** - Anxious genius who catches edge cases, seeks approval, obsessively documents
- **Crewman T'Prel** - Overly literal Vulcan who over-explains but writes perfect technical docs

**Medical:**
- **Nurse Keiko Tanaka** - Warm, chatty, knows all the gossip (actually pattern recognition), perfect patient history recall
- **Medical Technician James Chen** - Chronically clumsy but flawless sterile technique and diagnostic accuracy

**Science:**
- (None assigned yet - can add as needed)

### How It Works

**Conversation Monitoring:**
- Engineering, Science, and Medical terminal conversations are automatically buffered
- Both Casey's messages and crew responses are stored
- Buffer keeps last 50 messages per department

**Task Detection:**

1. **Explicit Requests** (immediate):
   - "Rodriguez, can you document the flux capacitor changes?"
   - "T'Prel, analyze the warp field data"
   - Detected in real-time, spawns agent immediately

2. **Implied Work** (nightly roundup):
   - "We should document this"
   - "Someone needs to trace that memory leak"
   - "Need better test coverage here"
   - Haiku scans conversations nightly, extracts tasks, assigns crew

**Agent Capabilities:**

Background crew have these tools:
- `read_file` - Read code/docs
- `write_file` - Create or update files
- `list_directory` - Explore project structure
- `search_files` - Find code/docs
- `append_to_file` - Add to logs/notes
- `create_project_note` - Write shift notes (stored in `shift_notes/[department]/`)

They can:
- Read your actual code
- Write actual documentation
- Update actual project files
- Create shift reports

**Crew Complement Tracking:**
- Every interaction (named crew + background crew) tracked
- 7-day rolling average = current crew size
- Displayed on Bridge sidebar
- Fluctuates with activity (attrition, transfers)

---

## How to Use

### Talk to Alex/Mira/Ryn, Mention Work

```
You: "Alex, we need to document the new authentication system"
Alex: [responds]
[Background: Conversation buffered for Rodriguez/T'Prel]
```

### Explicit Request (Immediate)

```
You: "Rodriguez, can you create documentation for the auth system?"
[Rodriguez spawns immediately, uses tools, reports back]
```

### Nightly Roundup (Batch Processing)

**Manual trigger:**
```
POST /crew/roundup
```

**What happens:**
1. Haiku analyzes buffered conversations
2. Extracts actionable tasks
3. Assigns to least-busy crew members
4. Processes 2 high-priority tasks immediately
5. Generates shift reports for each department
6. Posts reports to department logs

### Check Crew Complement

```
GET /crew/complement
```

Returns:
```json
{
  "complement": 9,
  "named_crew_count": 7,
  "background_crew_count": 4,
  "interactions_7day": 42
}
```

### Process Pending Tasks

```
POST /crew/process-tasks?max_tasks=3
```

Spawns agents for up to 3 pending tasks from the queue.

### Generate Shift Report

```
POST /crew/shift-report/engineering
```

Creates shift report for engineering crew, shows:
- Days served
- Tasks completed
- Current workload
- Recent work

---

## Data Files

**`backend/crew_roster.json`**
- Background crew definitions (names, quirks, strengths, stats)
- Named crew list
- Crew complement stats

**`backend/shift_reports.json`**
- Nightly roundup results
- Department shift reports
- Last roundup timestamp

**`backend/work_queue.json`**
- Pending tasks (extracted but not yet done)
- Completed tasks (last 100)
- Conversation buffers (last 50 per department)

**`backend/shift_notes/[department]/`**
- Actual markdown notes created by crew
- Timestamped shift reports
- Project documentation

---

## Testing Roadmap

1. **Basic Request:**
   - Go to Engineering terminal
   - Say "Rodriguez, can you list the files in the backend directory?"
   - Watch him use `list_directory` tool and report back

2. **Documentation Task:**
   - Say "Someone should document the cabin system we just built"
   - Run `/crew/roundup`
   - Check `shift_notes/engineering/` for what Rodriguez writes

3. **Nightly Workflow:**
   - Have several conversations with Alex about work
   - Run `/crew/roundup`
   - Check what tasks Haiku extracted
   - See shift reports generated

4. **Crew Complement:**
   - Check Bridge sidebar
   - Should show 11 personnel (7 named + 4 background)
   - Interact with Rodriguez
   - See complement update

---

## Future Enhancements

- Auto-schedule nightly roundup (cron job)
- Background crew can ask questions if stuck
- Crew promotion system (gamma → beta shift)
- More specialized crew roles
- Crew can collaborate on tasks
- Integration with Mira's project board
- Visual in terminals when crew is working

---

## Philosophy

These aren't NPCs. They're people keeping the ship running.

Rodriguez has been here 0 days. He'll be here tomorrow. Or maybe he won't.

That's the point.
