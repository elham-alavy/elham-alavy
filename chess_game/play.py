import chess
import chess.svg
import os
import re
import requests
from collections import defaultdict

REPO        = os.environ["REPO"]
TOKEN       = os.environ["GITHUB_TOKEN"]
ISSUE_TITLE = os.environ["ISSUE_TITLE"]
ISSUE_NUM   = int(os.environ["ISSUE_NUMBER"])
ISSUE_USER  = os.environ["ISSUE_USER"]

HEADERS = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github+json"}
BASE    = "https://api.github.com"

def post_comment(body):
    requests.post(f"{BASE}/repos/{REPO}/issues/{ISSUE_NUM}/comments",
                  headers=HEADERS, json={"body": body})

def close_issue():
    requests.patch(f"{BASE}/repos/{REPO}/issues/{ISSUE_NUM}",
                   headers=HEADERS, json={"state": "closed"})

def react(reaction="eyes"):
    requests.post(f"{BASE}/repos/{REPO}/issues/{ISSUE_NUM}/reactions",
                  headers=HEADERS, json={"content": reaction})

PIECE_NAMES = {
    chess.PAWN: "Pawn", chess.KNIGHT: "Knight", chess.BISHOP: "Bishop",
    chess.ROOK: "Rook", chess.QUEEN: "Queen",   chess.KING: "King",
}
WHITE_EMOJI = {
    chess.PAWN: "♙", chess.KNIGHT: "♘", chess.BISHOP: "♗",
    chess.ROOK: "♖", chess.QUEEN:  "♕", chess.KING:   "♔",
}
BLACK_EMOJI = {
    chess.PAWN: "♟", chess.KNIGHT: "♞", chess.BISHOP: "♝",
    chess.ROOK: "♜", chess.QUEEN:  "♛", chess.KING:   "♚",
}

def generate_svg(board, last_move=None):
    lm = chess.Move.from_uci(last_move) if last_move else None
    svg = chess.svg.board(
        board,
        lastmove=lm,
        size=400,
        colors={
            "square light":         "#f0d9b5",
            "square dark":          "#b58863",
            "square light lastmove":"#cdd26a",
            "square dark lastmove": "#aaa23a",
            "margin":               "#212121",
            "coord":                "#a0a0a0",
        },
    )
    with open("chess_game/board.svg", "w") as f:
        f.write(svg)

def move_links_by_piece(board):
    moves_by_piece = defaultdict(lambda: defaultdict(list))
    for move in board.legal_moves:
        piece = board.piece_at(move.from_square)
        if piece:
            moves_by_piece[piece.piece_type][chess.square_name(move.from_square)].append(
                chess.square_name(move.to_square)
            )
    emoji_map = WHITE_EMOJI if board.turn == chess.WHITE else BLACK_EMOJI
    lines = ["| | From | Moves |", "| :-: | :-: | --- |"]
    for pt in [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN, chess.KING]:
        if pt not in moves_by_piece:
            continue
        for from_sq in sorted(moves_by_piece[pt].keys()):
            tos = sorted(moves_by_piece[pt][from_sq])
            links = " · ".join(
                f"[**{to.upper()}**](https://github.com/{REPO}/issues/new?title=chess%7Cmove%7C{from_sq}{to}&body=Click+Submit+to+play!)"
                for to in tos
            )
            lines.append(f"| {emoji_map[pt]} | **{from_sq.upper()}** | {links} |")
    return "\n".join(lines)

def build_chess_section(board, last_move=None, move_num=0):
    turn      = "⬜ WHITE" if board.turn == chess.WHITE else "⬛ BLACK"
    last_str  = f"`{last_move[0:2].upper()}→{last_move[2:4].upper()}`" if last_move else "—"
    board_url = f"https://raw.githubusercontent.com/{REPO}/main/chess_game/board.svg"

    if board.is_game_over():
        result = board.result()
        return f"""### ♟️ Community Chess — Anyone Can Play!

<div align="center">

**Game over · Result: {result}** — thanks for playing!

<img src="{board_url}" width="360"/>

[![▶ New Game](https://img.shields.io/badge/▶_Start_New_Game-00ff88?style=for-the-badge)](https://github.com/{REPO}/issues/new?title=chess%7Cnew&body=Click+Submit+to+start+a+new+game!)

</div>
"""
    return f"""### ♟️ Community Chess — Anyone Can Play!

<div align="center">

| {turn}'s turn | Move **#{move_num + 1}** | Last move: {last_str} |
| :-----------: | :-------: | :----------: |

<img src="{board_url}" width="360"/>

</div>

> Click a destination square below, then hit **Submit new issue** — no text needed.

{move_links_by_piece(board)}

<div align="center">

[![🔄 Reset Game](https://img.shields.io/badge/🔄_Reset_Game-555?style=flat-square)](https://github.com/{REPO}/issues/new?title=chess%7Cnew&body=Click+Submit+to+reset.)

</div>
"""

# ── Main ──────────────────────────────────────────────────────────────────────

react("eyes")

parts    = ISSUE_TITLE.split("|")
command  = parts[1].strip() if len(parts) > 1 else ""
move_uci = parts[2].strip() if len(parts) > 2 else ""

fen_path       = "chess_game/board.fen"
last_move_path = "chess_game/last_move.txt"

board     = chess.Board()
last_move = None

if os.path.exists(fen_path) and command == "move":
    with open(fen_path) as f:
        saved = f.read().strip()
    if saved:
        board = chess.Board(saved)

if os.path.exists(last_move_path):
    with open(last_move_path) as f:
        last_move = f.read().strip() or None

if command == "new":
    board     = chess.Board()
    last_move = None
    post_comment(f"@{ISSUE_USER} New game started! ♟️ White moves first.")
elif command == "move":
    try:
        move = chess.Move.from_uci(move_uci)
        if move not in board.legal_moves:
            post_comment(f"@{ISSUE_USER} ❌ Illegal move: `{move_uci}`. [Try again.](https://github.com/{REPO})")
            close_issue()
            exit(0)
        board.push(move)
        last_move = move_uci
        post_comment(f"@{ISSUE_USER} ✅ Move `{move_uci[0:2].upper()}→{move_uci[2:4].upper()}` played! [View the board.](https://github.com/{REPO})")
    except Exception:
        post_comment(f"@{ISSUE_USER} ❌ Invalid move format: `{move_uci}`.")
        close_issue()
        exit(0)
else:
    post_comment(f"@{ISSUE_USER} Unknown command.")
    close_issue()
    exit(0)

with open(fen_path, "w") as f:
    f.write(board.fen())

with open(last_move_path, "w") as f:
    f.write(last_move or "")

generate_svg(board, last_move)

move_num      = len(board.move_stack)
chess_section = build_chess_section(board, last_move, move_num)

readme_path = "README.md"
with open(readme_path) as f:
    readme = f.read()

START = "<!-- CHESS_START -->"
END   = "<!-- CHESS_END -->"
block = f"{START}\n{chess_section}\n{END}"

if START in readme:
    readme = re.sub(re.escape(START) + ".*?" + re.escape(END), block, readme, flags=re.DOTALL)
else:
    readme += f"\n\n{block}\n"

with open(readme_path, "w") as f:
    f.write(readme)

close_issue()
