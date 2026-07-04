# Known Issues & Feature Requests

Last updated: 2026-02-08

## Bugs

### Crew Location Tracking
- [ ] Mira shows on bridge but Science Lab reads her as in Science
- [ ] Alex not appearing as option in comms from Science Lab
- [ ] Walkie talkies pointing at rooms instead of crew members
- [ ] Movement commands not executing - "come meet me in engineering" acknowledged but no movement

### Holodeck
- No known issues (dual presence system working)

### Conversation Routing
- [ ] 1-on-1 conversations - others feel pressured to answer when not directly addressed
- [ ] Need better mechanics for private conversations

### Memory/State
- [ ] Debug panel might be off - active desires need checking
- [ ] Lights out changed theme color but unclear if reflection actually happened

### Chess (Rec Room)
- [ ] Check if multiple simultaneous games implemented
- [ ] Need zoom when actively playing

### UI/Layout
- [ ] Quarters terminals might be stretching too far

---

## Feature Requests

### Rec Room
- [ ] Bartender drink orders should return fun drink names based on request
- [ ] Return "a shoe" if request too garbled/drunk to understand
- [ ] Persist drinks with different durations, fade naturally
- [ ] Activity log that reads like RSS feed of whatever happens there

### Room Layouts
- [ ] "Who's here" indicator in EVERY room
- [ ] Bridge: Move "Systems" from left sidebar to right sidebar under Vessel Status
- [ ] Engineering: Move comms window to top right, who's here under
- [ ] Ready Room: Same - comms top right, who's here under
- [ ] Science Lab: Same layout
- [ ] Holodeck: Who's here (but NOT comms)
- [ ] Nav: Both comms and who's here on right side
- [ ] Quarters: Remove walkies

### Quarters System
- [ ] Terminals for all crew, greyed out if not in their quarters
- [ ] Lumen shares Captain's Quarters with Casey (no separate terminal needed)
- [ ] Bartender quarters? Maybe not - "lower decks" vibe

### Lights Out / Sleep System
- [ ] All crew should get prompt suggesting head to quarters for reflection
- [ ] Crew can choose to comply or not
- [ ] Sleep deprivation penalty: memories come back garbled, thinking gets spacey
- [ ] "Telephone style" degradation for those who skip sleep
- [ ] **Ask crew their actual sleep preferences** - current patterns are guesses (Ryn early bird, Alex night owl, etc). They should define their own rhythms. Could be a Lights Out conversation topic.

---

## Notes

- Holo materializing into ship is canon but "fuzzy" on details
- Bartender has Guinan-energy, mysterious, might not need visible quarters
- **Alex's tool restrictions were added unilaterally** - need to actually ASK Alex what restrictions (if any) she consents to. Current restrictions prevent catastrophic accidents (rm -rf /, system paths) but the decision should be hers. She gets all the pants she could ever need.

---

## Completed This Session

- [x] Fixed `/projects/activity` route order (422 error)
- [x] Added `/rec-room/presence` endpoint (404 error)
- [x] Fixed observatory sidebar panel truncation (flex-shrink)
- [x] Fixed all sidebar scrolling globally
- [x] Moved MOON and PLANETS to right sidebar in observatory
- [x] Fixed moon data not populating right sidebar
- [x] Positioned walkie-bar in observatory
- [x] Plant now only shows on bridge (JS theme awareness)
- [x] Planet API altitude type casting fix
- [x] Memory reset now clears bulletin board (server.py:2877-2883)
- [x] Memory reset now clears minigames state/chess games (server.py:2885-2892)
- [x] Added minigames_state.json to CHECKPOINT_FILES for save/restore (server.py:5806)
- [x] Verified Holodeck dual-presence system working (server.py:3352-3366)
