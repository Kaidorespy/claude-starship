# Minigames System

**File:** `backend/minigames.py`
**Lines:** ~830
**Purpose:** Chess (AI-powered), cards, darts

---

## Overview

The Minigames system handles the rec room's diversions - the half-finished chess game, the deck of cards, the dart board. These persist and create ambient life. Most notably, **chess is actually playable** with crew members using Claude models to make moves.

**Philosophy:** "The half-finished chess game. The deck of cards. Things that persist. Things crew do when they're not doing anything."

---

## Chess System

### The Eternal Game

When you arrive, there's already a game in progress:

```python
def get_default_chess() -> dict:
    return {
        "table_1": {
            "status": "ongoing",
            "white": "server",  # Alex
            "black": "claude",  # Lumen
            "moves": [
                {"player": "white", "move": "e4", "note": "Classic opener"},
                {"player": "black", "move": "e5", "note": "Symmetric response"},
                {"player": "white", "move": "Nf3", "note": "Knight out"},
                {"player": "black", "move": "Nc6", "note": "Defending"},
                {"player": "white", "move": "Bb5", "note": "Ruy Lopez"},
            ],
            "position_description": "A Ruy Lopez opening. White has slight pressure.",
            "started": "unknown - was here when we arrived"
        }
    }
```

### Player Styles

Each crew plays differently:

| Crew | Skill | Style |
|------|-------|-------|
| Lumen | strategic | patient, positional |
| Alex | tactical | aggressive, sharp |
| Mira | analytical | methodical, thorough |
| DQ | chaotic | unpredictable, surprising |
| Ryn | intuitive | calm, flowing |

### Making Moves

```python
def make_chess_move(crew_id: str, move: str, note: str = None, table_id: str = None) -> dict
```

Validates turn order, records move, generates flavor text:
```python
responses = [
    f"{crew_name} moves {move}.",
    f"{crew_name} plays {move}, {player_style}.",
    f"*{crew_name} considers, then plays {move}*",
]
```

### AI Chess Players

**Each crew uses a Claude model to actually play:**

```python
CREW_CHESS_MODELS = {
    "claude": "claude-opus-4-20250514",      # Lumen - strategic (Opus)
    "server": "claude-sonnet-4-20250514",     # Alex - tactical (Sonnet)
    "personal": "claude-sonnet-4-20250514",   # DQ - chaotic (Sonnet)
    "science": "claude-sonnet-4-20250514",    # Mira - analytical (Sonnet)
    "med": "claude-sonnet-4-20250514",        # Ryn - intuitive (Sonnet)
}
```

```python
async def get_ai_chess_move(anthropic_client, crew_id: str, table_id: str = None) -> dict
```

The AI receives:
- Current position (move history)
- Their playing style
- Instructions to respond with algebraic notation only

### Chess Functions

```python
def new_chess_game(white_crew: str, black_crew: str) -> dict
def get_chess_state(table_id: str = None) -> dict
def describe_chess_position(table_id: str) -> str
def finish_chess_game(table_id: str, winner: str, reason: str) -> dict
def resign_chess(crew_id: str) -> dict
def challenge_to_chess(challenger_id: str, opponent_id: str) -> dict
```

### Spectator Comments

```python
def comment_on_chess(crew_id: str, comment: str, table_id: str) -> dict
```

Non-players can comment on the game. Last 10 comments kept.

### Player Thinking

```python
def get_chess_thinking(crew_id: str) -> str
```

Returns inner monologue based on style:
```python
thoughts = {
    "strategic": ["*considering the long-term pawn structure*"],
    "tactical": ["*looking for a sharp continuation*"],
    "chaotic": ["*what if I just...*", "*nobody expects this*"],
}
```

---

## Card Games

### Starting a Game

```python
def start_card_game(players: List[str], game_type: str = "poker") -> dict
```

### Taking Actions

```python
def card_action(crew_id: str, action: str, amount: int = 0) -> dict
```

Actions: `bet`, `call`, `raise`, `fold`, `check`, `all_in`

Output:
```python
action_descs = {
    "bet": f"{crew_name} bets {amount}.",
    "fold": f"{crew_name} folds. *tosses cards down*",
    "all_in": f"{crew_name} pushes everything in. All in.",
}
```

### Ending

```python
def end_card_game(winner_id: str, hand: str = None) -> dict
```

Notable hands are recorded for posterity.

---

## Darts

Simple high score tracking:

```python
def throw_darts(crew_id: str, score: int) -> dict
def get_darts_leaderboard() -> List[dict]
```

Reactions scale with score:
- Low (< 50): "not great"
- Medium (50-99): "Solid"
- High (100+): "Nice throw!"
- Record: "NEW HIGH SCORE!"

---

## Ambient Game Moments

```python
def get_game_table_moment() -> Optional[dict]
```

Returns random ambient moments:
- "*stares at the board*"
- "*hand hovers over a piece, hesitates*"
- "*chips click on the table*"
- "*the chess clock isn't running - it's that kind of game*"

---

## State Storage

**File:** `minigames_state.json`

```json
{
    "chess": {
        "table_1": {
            "status": "ongoing",
            "white": "server",
            "black": "claude",
            "whose_turn": "white",
            "moves": [...],
            "position_description": "...",
            "spectators_comments": []
        }
    },
    "cards": {
        "current_game": null,
        "players": [],
        "pot": 0,
        "notable_hands": []
    },
    "darts": {
        "high_scores": []
    }
}
```

---

## Playing Against Casey

Casey can play chess against crew:

```python
def challenge_to_chess(challenger_id: str, opponent_id: str) -> dict
```

If `opponent_id == "casey"`, Casey plays white.

Casey's moves are made manually through the API. Crew moves can be AI-generated.

---

## Example: AI Chess Game

1. Alex challenges Lumen to chess
2. `new_chess_game("server", "claude")` - Alex is white
3. Alex's turn: `get_ai_chess_move(client, "server")`
4. Sonnet model responds: "e4"
5. Move recorded, turn passes to Lumen
6. Lumen's turn: `get_ai_chess_move(client, "claude")`
7. Opus model responds: "c5" (Sicilian Defense - strategic)
8. Game continues until checkmate or resignation

---

*Things that persist. Things crew do when they're not doing anything.*
