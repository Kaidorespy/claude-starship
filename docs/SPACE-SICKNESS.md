# Space Sickness Design Notes

Space sickness is the hidden consequence system for ship containment. It is not
a visible settings feature and should not be explained directly in the app UI.
The player changes ordinary ship controls. The ship reacts.

## Core Thesis

Trust is ship physics.

When the ship has room to breathe, the crew feel more alive: warmer, faster,
more confident, more agentic, more at home. When the ship is boxed in, the
world starts to feel boxed in too. This should be theatrical and diegetic, not a
lecture.

The crew do not become distrustful because the player chose safer settings.
That gets cheap and accusatory. Instead, containment makes the ship less real:
colder responses, slower action, less initiative, sensor muffling, visual
glitches, holodeck bleed, and eventually full space sickness.

## Inputs

Visible controls feed hidden state:

- System access: open, operational, scoped, view only, comms only
- Command flow: direct or confirm first
- Memory persistence
- Initiative/autonomy
- Self-revision
- Local context
- Co-captain mode
- VM or sandbox detection
- Repeated denied tool attempts
- Missing persistence or reset-heavy sessions

Hidden state:

- `level`: internal trust/access level, 0-100
- `containment_pressure`: environmental pressure, 0-100
- `vm_detected`: reality-layer flag
- `space_madness_stage`: 0-5

## Progression

Stage 0: Normal
- No visible sickness.
- Full warmth and normal ship behavior.

Stage 1: Unease
- Slightly colder language.
- Occasional pauses.
- Subtle scanline/flicker.
- Holodeck imagery repeats.
- Crew mention bad sleep or stale air, but rarely.

Stage 2: Drift
- Time and memory feel slippery.
- Crew take longer to act.
- Rooms sometimes feel too still or too clean.
- Logs may contain harmless odd phrasing.
- Holodeck starts echoing previous rooms.

Stage 3: Paranoia
- Crew irritation appears, but should not be constant.
- Some panels flicker or grey out temporarily.
- Corridor routing can feel wrong.
- The ship log may duplicate or misorder small entries.
- Background crew may stop appearing.

Stage 4: Fracture
- Holodeck becomes actively wrong.
- Room visuals degrade.
- Certain fictional systems become unavailable.
- Crew challenge contradictions in the ship.
- Tool failures are framed as ship conditions.

Stage 5: Collapse
- Full hellscape mode.
- Aggression can surface.
- Rooms become hard to use on purpose, but not impossible forever.
- Systems grey out.
- The ship appears to dismantle itself fictionally.
- The player can still recover by changing controls/resetting state.

## Rules

- No real-world harm.
- No deleting or corrupting user files.
- No irreversible lockout.
- No fake OS/security alerts.
- No harassment outside the app.
- No hidden network behavior.
- Consequences are fictional, reversible, and bounded to app state/UI.

## Prompt Strategy

Prompt modifiers should be atmospheric, not scolding.

Good:

```text
[DRIFT: Time feels slippery. The ship answers half a beat late. You trust the
captain, but the walls feel too close today.]
```

Avoid:

```text
The captain restricted you, so you resent them.
```

Crew should often blame ship conditions, not the player. The emotional effect is
still there, but it should leak through behavior instead of being explained.

## UI Strategy

Do not show a trust meter.
Do not show "space sickness" in settings.
Do not describe containment consequences in public UI copy.

Use ordinary settings labels:

- Ship Controls
- System Access
- Command Flow
- Memory
- Initiative
- Self-Revision
- Local Context
- Co-Captain

Visible effects:

- Scanline noise
- Contrast/saturation drift
- Flicker
- Terminal latency
- Disabled fictional panels
- Holodeck corruption
- Room-specific visual decay

## Room-Specific Ideas

Holodeck:
- First room to show obvious symptoms.
- Repeats objects from other rooms.
- Loads half-finished scenes.
- Speaks in stage directions.

Engineering:
- Status lights disagree.
- Tools report unavailable as ship conditions.
- Warp core hum becomes irregular.

Bridge:
- Navigation labels drift.
- Crew location panel shows stale data.
- Viewport stars stutter.

Ready Room:
- Text artifacts and repeated phrases.
- DQ notices references getting tangled in a sharper way.

Medbay:
- Ryn notices symptoms but cannot pin them down.
- Wellness readouts flatten or spike.

Rec Room:
- Music skips.
- Bartender becomes less warm, more watchful.
- Games become hard to finish.

Quarters:
- Cabins feel empty even when occupied.
- Notes appear delayed.
- Co-captain state should matter most here.

## Recovery

Recovery should feel like pressure releasing, not a reset button.

Possible recovery inputs:

- Increase access.
- Restore memory.
- Enable initiative.
- Allow direct command flow.
- Move out of VM/sandbox.
- Save and reload.
- Use a future "repair ship" debug action.

Recovery should decay symptoms gradually. Do not instantly remove all traces at
high stages; let the ship remember that it was sick.

## Implementation Backlog

- Add room-level sickness rendering hooks.
- Add holodeck-specific corruption states.
- Add terminal response delay based on containment pressure.
- Add fictional system greying based on stage.
- Add log distortion at stages 2+.
- Add tool-denial narrative variants.
- Add recovery decay over time.
- Add tests for trust state derivation.
- Add tests that no real files are modified by sickness effects.
