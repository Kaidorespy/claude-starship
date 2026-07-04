"""
Minigames - The Rec Room's Diversions

The half-finished chess game. The deck of cards.
Things that persist. Things crew do when they're not doing anything.
"""

import json
import random
from datetime import datetime
from pathlib import Path
try:
    from .paths import data_path
except ImportError:
    from paths import data_path
from typing import Optional, List

MINIGAMES_FILE = data_path("minigames_state.json")

# Crew display names
CREW_NAMES = {
    "claude": "Lumen",
    "server": "Alex",
    "personal": "DQ",
    "science": "Mira",
    "games": "Holodeck",
    "med": "Ryn",
    "rec": "The Bartender",
}

# Who plays what
CHESS_PLAYERS = {
    "claude": {"skill": "strategic", "style": "patient, positional"},
    "server": {"skill": "tactical", "style": "aggressive, sharp"},
    "science": {"skill": "analytical", "style": "methodical, thorough"},
    "personal": {"skill": "chaotic", "style": "unpredictable, surprising"},
    "med": {"skill": "intuitive", "style": "calm, flowing"},
}


def load_state() -> dict:
    if MINIGAMES_FILE.exists():
        try:
            with open(MINIGAMES_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "chess": get_default_chess(),
        "cards": get_default_cards(),
        "darts": {"high_scores": []},
    }


def save_state(state: dict):
    with open(MINIGAMES_FILE, 'w') as f:
        json.dump(state, f, indent=2)


# === CHESS ===
# The half-finished game that's been going for who knows how long

def get_default_chess() -> dict:
    """Default: the game that was here when we arrived."""
    return {
        "table_1": {
            "id": "table_1",
            "status": "ongoing",
            "white": "server",  # Alex
            "black": "claude",  # Lumen
            "whose_turn": "white",
            "moves": [
                {"player": "white", "move": "e4", "note": "Classic opener"},
                {"player": "black", "move": "e5", "note": "Symmetric response"},
                {"player": "white", "move": "Nf3", "note": "Knight out"},
                {"player": "black", "move": "Nc6", "note": "Defending"},
                {"player": "white", "move": "Bb5", "note": "Ruy Lopez"},
            ],
            "position_description": "A Ruy Lopez opening. White has slight pressure. Black is solid.",
            "mood": "contemplative",
            "started": "unknown - was here when we arrived",
            "last_move_time": None,
            "spectators_comments": [],
        }
    }


def get_available_table() -> str:
    """Find an available table or create a new one."""
    state = load_state()
    chess = state.get("chess", {})

    # Find empty table or finished game
    for table_id, game in chess.items():
        if game.get("status") in ["finished", "abandoned", None]:
            return table_id

    # Create new table
    table_num = len(chess) + 1
    return f"table_{table_num}"


def get_player_game(crew_id: str) -> Optional[tuple]:
    """Find which game a player is in. Returns (table_id, game) or None."""
    state = load_state()
    chess = state.get("chess", {})

    for table_id, game in chess.items():
        if game.get("status") == "ongoing":
            if game.get("white") == crew_id or game.get("black") == crew_id:
                return (table_id, game)
    return None


def get_chess_state(table_id: str = None) -> dict:
    """Get chess game state. If no table specified, returns all active games."""
    state = load_state()
    chess = state.get("chess", get_default_chess())

    if table_id:
        # Get specific table
        game = chess.get(table_id)
        if not game:
            return {"error": "Table not found"}
        return format_game_state(table_id, game)

    # Return all active games
    active_games = []
    for tid, game in chess.items():
        if game.get("status") == "ongoing":
            active_games.append(format_game_state(tid, game))

    return {
        "active_games": active_games,
        "total_tables": len(chess)
    }


def format_game_state(table_id: str, game: dict) -> dict:
    """Format a single game's state."""
    white_name = CREW_NAMES.get(game.get("white", ""), "White")
    if game.get("white") == "casey":
        white_name = "Casey"
    black_name = CREW_NAMES.get(game.get("black", ""), "Black")
    if game.get("black") == "casey":
        black_name = "Casey"

    whose_turn = game.get("whose_turn", "white")
    turn_name = white_name if whose_turn == "white" else black_name

    return {
        "table_id": table_id,
        **game,
        "white_name": white_name,
        "black_name": black_name,
        "turn_name": turn_name,
        "move_count": len(game.get("moves", [])),
    }


def make_chess_move(crew_id: str, move: str, note: str = None, table_id: str = None) -> dict:
    """
    Make a chess move.
    Move is in algebraic notation (e4, Nf3, Bxc6, O-O, etc.)
    If no table_id, finds the player's current game.
    """
    state = load_state()
    chess = state.get("chess", get_default_chess())

    # Find the game
    if table_id:
        if table_id not in chess:
            return {"error": "Table not found"}
        game = chess[table_id]
    else:
        # Find player's game
        player_game = get_player_game(crew_id)
        if not player_game:
            return {"error": f"{CREW_NAMES.get(crew_id, crew_id)} is not in a game"}
        table_id, game = player_game

    # Check if it's their turn
    white = game.get("white")
    black = game.get("black")
    whose_turn = game.get("whose_turn", "white")

    if whose_turn == "white" and crew_id != white:
        white_name = "Casey" if white == "casey" else CREW_NAMES.get(white, 'White')
        return {"error": f"It's {white_name}'s turn"}
    if whose_turn == "black" and crew_id != black:
        black_name = "Casey" if black == "casey" else CREW_NAMES.get(black, 'Black')
        return {"error": f"It's {black_name}'s turn"}

    # Record the move
    crew_name = "Casey" if crew_id == "casey" else CREW_NAMES.get(crew_id, crew_id)
    player_style = CHESS_PLAYERS.get(crew_id, {}).get("style", "thoughtful")

    move_record = {
        "player": whose_turn,
        "crew_id": crew_id,
        "move": move,
        "note": note,
        "timestamp": datetime.now().isoformat(),
    }

    game["moves"].append(move_record)
    game["whose_turn"] = "black" if whose_turn == "white" else "white"
    game["last_move_time"] = datetime.now().isoformat()

    chess[table_id] = game
    state["chess"] = chess
    save_state(state)

    # Generate response
    responses = [
        f"{crew_name} moves {move}.",
        f"{crew_name} plays {move}, {player_style}.",
        f"*{crew_name} considers, then plays {move}*",
        f"{move}. {crew_name} leans back.",
    ]

    next_player = game["whose_turn"]
    next_id = white if next_player == "white" else black
    next_name = "Casey" if next_id == "casey" else CREW_NAMES.get(next_id, next_id)

    return {
        "status": "moved",
        "table_id": table_id,
        "move": move,
        "player": crew_name,
        "description": random.choice(responses),
        "next_turn": next_name,
        "move_count": len(game["moves"])
    }


def finish_chess_game(table_id: str, winner: str, reason: str = "checkmate") -> dict:
    """End a chess game with a winner."""
    state = load_state()
    chess = state.get("chess", {})

    if table_id not in chess:
        return {"error": "Table not found"}

    game = chess[table_id]
    game["status"] = "finished"
    game["winner"] = winner
    game["end_reason"] = reason
    game["ended"] = datetime.now().isoformat()

    chess[table_id] = game
    state["chess"] = chess
    save_state(state)

    winner_name = "Casey" if winner == "casey" else CREW_NAMES.get(winner, winner)

    return {
        "status": "game_over",
        "table_id": table_id,
        "winner": winner_name,
        "reason": reason,
        "moves": len(game.get("moves", []))
    }


def resign_chess(crew_id: str, table_id: str = None) -> dict:
    """Resign from a chess game."""
    player_game = get_player_game(crew_id) if not table_id else None
    if not table_id:
        if not player_game:
            return {"error": "Not in a game"}
        table_id, game = player_game
    else:
        state = load_state()
        game = state.get("chess", {}).get(table_id)
        if not game:
            return {"error": "Table not found"}

    # Determine winner (opponent)
    white = game.get("white")
    black = game.get("black")
    winner = black if crew_id == white else white

    crew_name = "Casey" if crew_id == "casey" else CREW_NAMES.get(crew_id, crew_id)

    result = finish_chess_game(table_id, winner, reason=f"{crew_name} resigned")
    result["resigned"] = crew_name

    return result


def comment_on_chess(crew_id: str, comment: str, table_id: str = "table_1") -> dict:
    """A spectator comments on the game."""
    state = load_state()
    chess = state.get("chess", get_default_chess())

    if table_id not in chess:
        return {"error": "Table not found"}

    game = chess[table_id]
    crew_name = "Casey" if crew_id == "casey" else CREW_NAMES.get(crew_id, crew_id)

    if "spectators_comments" not in game:
        game["spectators_comments"] = []

    game["spectators_comments"].append({
        "crew_id": crew_id,
        "crew_name": crew_name,
        "comment": comment,
        "timestamp": datetime.now().isoformat()
    })

    # Keep last 10 comments
    game["spectators_comments"] = game["spectators_comments"][-10:]

    chess[table_id] = game
    state["chess"] = chess
    save_state(state)

    return {
        "status": "commented",
        "table_id": table_id,
        "from": crew_name,
        "comment": comment
    }


def describe_chess_position(table_id: str = "table_1") -> str:
    """Describe the current chess position narratively."""
    state = load_state()
    chess = state.get("chess", get_default_chess())

    if table_id not in chess:
        return "No game at this table."

    game = chess[table_id]

    if game.get("status") == "finished":
        winner = game.get("winner", "someone")
        winner_name = "Casey" if winner == "casey" else CREW_NAMES.get(winner, winner)
        return f"Game over. {winner_name} won. {game.get('end_reason', '')}"

    move_count = len(game.get("moves", []))
    white_name = "Casey" if game.get("white") == "casey" else CREW_NAMES.get(game.get("white"), "White")
    black_name = "Casey" if game.get("black") == "casey" else CREW_NAMES.get(game.get("black"), "Black")
    whose_turn = game.get("whose_turn", "white")
    turn_name = white_name if whose_turn == "white" else black_name

    base_desc = game.get("position_description", "A game in progress.")

    if move_count < 10:
        phase = "opening"
        tension = "The game is still young."
    elif move_count < 25:
        phase = "middlegame"
        tension = "Things are getting interesting."
    else:
        phase = "endgame"
        tension = "Every move matters now."

    last_move = game.get("moves", [])[-1] if game.get("moves") else None
    last_move_desc = ""
    if last_move:
        mover = last_move.get('crew_id', '')
        mover_name = "Casey" if mover == "casey" else CREW_NAMES.get(mover, 'someone')
        last_move_desc = f"Last move: {last_move.get('move')} by {mover_name}."

    return f"{base_desc} {tension} {last_move_desc} {turn_name}'s turn."


def get_chess_thinking(crew_id: str) -> str:
    """What is this player thinking about the position?"""
    style = CHESS_PLAYERS.get(crew_id, {})
    skill = style.get("skill", "thoughtful")
    manner = style.get("style", "careful")

    thoughts = {
        "strategic": [
            "*considering the long-term pawn structure*",
            "*thinking three moves ahead*",
            "*this position needs patience*",
        ],
        "tactical": [
            "*looking for a sharp continuation*",
            "*there might be something here...*",
            "*aggressive options...*",
        ],
        "analytical": [
            "*calculating variations*",
            "*evaluating piece activity*",
            "*systematic approach needed*",
        ],
        "chaotic": [
            "*what if I just...*",
            "*nobody expects this*",
            "*rules are guidelines anyway*",
        ],
        "intuitive": [
            "*this feels right*",
            "*following the flow*",
            "*the position speaks*",
        ],
    }

    return random.choice(thoughts.get(skill, ["*thinking*"]))


def new_chess_game(white_crew: str, black_crew: str) -> dict:
    """Start a new chess game at an available table."""
    state = load_state()
    if "chess" not in state:
        state["chess"] = {}

    # Check if either player is already in a game
    for player in [white_crew, black_crew]:
        existing = get_player_game(player)
        if existing:
            player_name = "Casey" if player == "casey" else CREW_NAMES.get(player, player)
            return {"error": f"{player_name} is already in a game at {existing[0]}"}

    table_id = get_available_table()

    state["chess"][table_id] = {
        "id": table_id,
        "status": "ongoing",
        "white": white_crew,
        "black": black_crew,
        "whose_turn": "white",
        "moves": [],
        "position_description": "A fresh board. Everything is possible.",
        "mood": "anticipation",
        "started": datetime.now().isoformat(),
        "last_move_time": None,
        "spectators_comments": [],
    }

    save_state(state)

    white_name = "Casey" if white_crew == "casey" else CREW_NAMES.get(white_crew, white_crew)
    black_name = "Casey" if black_crew == "casey" else CREW_NAMES.get(black_crew, black_crew)

    return {
        "status": "new_game",
        "table_id": table_id,
        "white": white_name,
        "black": black_name,
        "message": f"New game at {table_id}: {white_name} (white) vs {black_name} (black). {white_name} to move."
    }


# === CARDS ===
# Poker, or whatever they're playing

def get_default_cards() -> dict:
    return {
        "current_game": None,
        "players": [],
        "pot": 0,
        "last_winner": None,
        "notable_hands": [],
    }


def start_card_game(players: List[str], game_type: str = "poker") -> dict:
    """Start a card game."""
    state = load_state()

    player_names = [CREW_NAMES.get(p, p) for p in players]

    state["cards"] = {
        "current_game": game_type,
        "players": players,
        "player_names": player_names,
        "pot": 0,
        "round": 1,
        "status": "playing",
        "started": datetime.now().isoformat(),
        "last_action": None,
    }

    save_state(state)

    return {
        "status": "started",
        "game": game_type,
        "players": player_names,
        "message": f"{game_type.title()} night. {', '.join(player_names)} around the table."
    }


def card_action(crew_id: str, action: str, amount: int = 0) -> dict:
    """
    Take an action in the card game.
    Actions: bet, call, raise, fold, check
    """
    state = load_state()
    cards = state.get("cards", get_default_cards())

    if not cards.get("current_game"):
        return {"error": "No game in progress"}

    if crew_id not in cards.get("players", []):
        return {"error": "You're not in this game"}

    crew_name = CREW_NAMES.get(crew_id, crew_id)

    action_descs = {
        "bet": f"{crew_name} bets {amount}.",
        "call": f"{crew_name} calls.",
        "raise": f"{crew_name} raises to {amount}.",
        "fold": f"{crew_name} folds. *tosses cards down*",
        "check": f"{crew_name} checks.",
        "all_in": f"{crew_name} pushes everything in. All in.",
    }

    if action == "bet" or action == "raise" or action == "all_in":
        cards["pot"] = cards.get("pot", 0) + amount

    cards["last_action"] = {
        "crew_id": crew_id,
        "action": action,
        "amount": amount,
        "timestamp": datetime.now().isoformat()
    }

    state["cards"] = cards
    save_state(state)

    return {
        "status": "action",
        "description": action_descs.get(action, f"{crew_name} does something."),
        "pot": cards["pot"]
    }


def end_card_game(winner_id: str, hand: str = None) -> dict:
    """End the card game with a winner."""
    state = load_state()
    cards = state.get("cards", get_default_cards())

    winner_name = CREW_NAMES.get(winner_id, winner_id)
    pot = cards.get("pot", 0)

    # Record notable hand
    if hand:
        cards["notable_hands"].append({
            "winner": winner_name,
            "hand": hand,
            "pot": pot,
            "timestamp": datetime.now().isoformat()
        })
        cards["notable_hands"] = cards["notable_hands"][-10:]

    cards["last_winner"] = winner_id
    cards["current_game"] = None
    cards["players"] = []
    cards["pot"] = 0

    state["cards"] = cards
    save_state(state)

    return {
        "status": "game_over",
        "winner": winner_name,
        "hand": hand,
        "pot": pot,
        "message": f"{winner_name} takes the pot{f' with {hand}' if hand else ''}."
    }


def get_cards_state() -> dict:
    """Get current card game state."""
    state = load_state()
    return state.get("cards", get_default_cards())


# === DARTS ===
# Simple high score tracker

def throw_darts(crew_id: str, score: int) -> dict:
    """Record a dart throw/round."""
    state = load_state()
    darts = state.get("darts", {"high_scores": []})

    crew_name = CREW_NAMES.get(crew_id, crew_id)

    # Check if high score
    high_scores = darts.get("high_scores", [])
    is_high = len(high_scores) == 0 or score > max(s.get("score", 0) for s in high_scores)

    darts["high_scores"].append({
        "crew_id": crew_id,
        "crew_name": crew_name,
        "score": score,
        "timestamp": datetime.now().isoformat()
    })

    # Keep top 10
    darts["high_scores"] = sorted(darts["high_scores"], key=lambda x: -x.get("score", 0))[:10]

    state["darts"] = darts
    save_state(state)

    reactions = {
        "low": [
            f"{crew_name} throws... not great.",
            f"*{crew_name}'s dart lands with a sad thunk*",
            f"{crew_name}: 'That one didn't count.'",
        ],
        "medium": [
            f"{crew_name} throws. Solid.",
            f"*{crew_name} nods, satisfied*",
            f"Not bad. {score} points.",
        ],
        "high": [
            f"{crew_name} throws! {score}!",
            f"*{crew_name} grins* That's how it's done.",
            f"Nice throw. {score} points.",
        ],
        "record": [
            f"{crew_name} THROWS! NEW HIGH SCORE! {score}!",
            f"*the bar goes quiet, then cheers*",
            f"{crew_name} just set the record. {score} points.",
        ]
    }

    if is_high and len(high_scores) > 0:
        reaction_type = "record"
    elif score >= 100:
        reaction_type = "high"
    elif score >= 50:
        reaction_type = "medium"
    else:
        reaction_type = "low"

    return {
        "score": score,
        "is_high_score": is_high,
        "reaction": random.choice(reactions[reaction_type]),
        "leaderboard_position": next(
            (i+1 for i, s in enumerate(darts["high_scores"]) if s.get("crew_id") == crew_id),
            None
        )
    }


def get_darts_leaderboard() -> List[dict]:
    """Get darts high scores."""
    state = load_state()
    darts = state.get("darts", {"high_scores": []})
    return darts.get("high_scores", [])


# === AMBIENT GAME MOMENTS ===
# Random things that might happen at the game table

# === AI CHESS PLAYER ===
# Each crew member's model actually plays chess

# Map crew to their model - different models = different playstyles
CREW_CHESS_MODELS = {
    "claude": "claude-opus-4-20250514",      # Lumen - thoughtful, strategic (Opus)
    "server": "claude-sonnet-4-20250514",     # Alex - tactical, sharp (Sonnet)
    "personal": "claude-sonnet-4-20250514",   # DQ - chaotic but fun (Sonnet)
    "science": "claude-sonnet-4-20250514",    # Mira - analytical (Sonnet)
    "med": "claude-sonnet-4-20250514",        # Ryn - intuitive (Sonnet)
}

CHESS_MOVE_PROMPT = """You are playing chess as {color}.

Current game state (moves so far in algebraic notation):
{moves}

{position_desc}

It's your turn. You play with a {style} style.

Reply with ONLY your move in standard algebraic notation (e.g., e4, Nf3, Bxc6, O-O, Qh5+).
Just the move, nothing else."""


async def get_ai_chess_move(anthropic_client, crew_id: str, table_id: str = None) -> Optional[dict]:
    """
    Get a chess move from the crew member's AI model.
    Returns the move or None if not their turn / error.
    """
    import asyncio

    # Find the player's game
    if table_id:
        state = load_state()
        chess = state.get("chess", {})
        if table_id not in chess:
            return None
        game = chess[table_id]
    else:
        player_game = get_player_game(crew_id)
        if not player_game:
            return None
        table_id, game = player_game

    # Check if it's their turn
    whose_turn = game.get("whose_turn", "white")
    white = game.get("white")
    black = game.get("black")

    if whose_turn == "white" and crew_id != white:
        return None
    if whose_turn == "black" and crew_id != black:
        return None

    # Build the prompt
    moves = game.get("moves", [])
    moves_str = ", ".join([m.get("move", "") for m in moves]) if moves else "None yet (opening move)"

    color = "white" if crew_id == white else "black"
    style_info = CHESS_PLAYERS.get(crew_id, {})
    style = style_info.get("style", "thoughtful")
    position_desc = game.get("position_description", "")

    prompt = CHESS_MOVE_PROMPT.format(
        color=color,
        moves=moves_str,
        position_desc=position_desc,
        style=style
    )

    # Get the model for this crew member
    model = CREW_CHESS_MODELS.get(crew_id, "claude-sonnet-4-20250514")

    try:
        def call_model():
            return anthropic_client.messages.create(
                model=model,
                max_tokens=20,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await asyncio.to_thread(call_model)
        move = response.content[0].text.strip()

        # Clean up the move (remove any extra text)
        move = move.split()[0] if move else None

        if move:
            # Make the move
            result = make_chess_move(crew_id, move, table_id=table_id)
            result["model_used"] = model
            result["ai_generated"] = True
            return result

    except Exception as e:
        print(f"[Chess AI] Failed to get move from {crew_id}: {e}", flush=True)

    return None


def challenge_to_chess(challenger_id: str, opponent_id: str) -> dict:
    """
    Challenge someone to a chess game.
    If opponent is 'casey', Casey plays white.
    """
    # Random who plays white
    if opponent_id == "casey":
        # Casey always plays white when challenged
        white = "casey"
        black = challenger_id
    elif challenger_id == "casey":
        white = "casey"
        black = opponent_id
    else:
        # Random between crew
        if random.random() < 0.5:
            white = challenger_id
            black = opponent_id
        else:
            white = opponent_id
            black = challenger_id

    result = new_chess_game(white, black)
    result["challenger"] = CREW_NAMES.get(challenger_id, challenger_id)
    result["opponent"] = CREW_NAMES.get(opponent_id, opponent_id) if opponent_id != "casey" else "Casey"

    return result


def get_game_table_moment() -> Optional[dict]:
    """Get a random moment happening at the game table."""
    state = load_state()
    chess = state.get("chess", {})

    moments = []

    # Chess moments
    if chess.get("status") == "ongoing":
        white = CREW_NAMES.get(chess.get("white", ""), "someone")
        black = CREW_NAMES.get(chess.get("black", ""), "someone")
        whose_turn = chess.get("whose_turn", "white")
        thinking = white if whose_turn == "white" else black

        chess_moments = [
            f"*{thinking} stares at the board*",
            f"*hand hovers over a piece, hesitates*",
            f"*{white} drums fingers, waiting*",
            f"*someone walks by, glances at the board, winces*",
            f"*the chess clock isn't running - it's that kind of game*",
            f"*{black} takes a long sip of their drink*",
        ]
        moments.extend(chess_moments)

    # Card moments
    cards = state.get("cards", {})
    if cards.get("current_game"):
        players = cards.get("player_names", [])
        if players:
            card_moments = [
                f"*chips click on the table*",
                f"*{random.choice(players)} maintains a perfect poker face*",
                f"*someone shuffles absently*",
                f"*tension at the card table*",
            ]
            moments.extend(card_moments)

    if not moments:
        moments = [
            "*the game table sits empty, waiting*",
            "*half-finished chess game, pieces patient*",
            "*a deck of cards, neatly stacked*",
        ]

    return {
        "type": "game_table_moment",
        "moment": random.choice(moments)
    }
