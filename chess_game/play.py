import chess
import os
import re
import requests
from collections import defaultdict

REPO        = os.environ["REPO"]
TOKEN       = os.environ["GITHUB_TOKEN"]
ISSUE_TITLE = os.environ["ISSUE_TITLE"]
ISSUE_NUM   = int(os.environ["ISSUE_NUMBER"])
ISSUE_USER  = os.environ["ISSUE_USER"]

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json",
}

BASE = "https://api.github.com"

def post_comment(body):
    requests.post(f"{BASE}/repos/{REPO}/issues/{ISSUE_NUM}/comments",
                  headers=HEADERS, json={"body": body})

def close_issue():
    requests.patch(f"{BASE}/repos/{REPO}/issues/{ISSUE_NUM}",
                   headers=HEADERS, json={"state": "closed"})

def react(reaction="eyes"):
    requests.post(f"{BASE}/repos/{REPO}/issues/{ISSUE_NUM}/reactions",
                  headers=HEADERS, json={"content": reaction})

PIECE_EMOJI = {
    (chess.KING,   chess.WHITE): "♔", (chess.QUEEN,  chess.WHITE): "♕",
    (chess.ROOK,   chess.WHITE): "♖", (chess.BISHOP, chess.WHITE): "♗",
    (chess.KNIGHT, chess.WHITE): "♘", (chess.PAWN,   chess.WHITE): "♙",
    (chess.KING,   chess.BLACK): "♚", (chess.QUEEN,  chess.BLACK): "♛",
    (chess.ROOK,   chess.BLACK): "♜", (chess.BISHOP, chess.BLACK): "♝",
    (chess.KNIGHT, chess.BLACK): "♞", (chess.PAWN,   chess.BLACK): "♟",
}

def board_to_markdown(board):
    lines = ["|   | a | b | c | d | e | f | g | h |",
             "|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|"]
    for rank in range(7, -1, -1):
        row = f"| **{rank+1}** |"
        for file in range(8):
            sq = chess.square(file, rank)
            piece = board.piece_at(sq)
            if piece:
                row += f" {PIECE_EMOJI[(piece.piece_type, piece.color)]} |"
            else:
                row += " ⬛ |" if (rank + file) % 2 == 0 else " ⬜ |"
        lines.append(row)
    return "\n".join(lines)

def move_links(board):
    moves_by_from = defaultdict(list)
    for move in board.legal_moves:
        moves_by_from[chess.square_name(move.from_square)].append(chess.square_name(move.to_square))
    lines = ["| FROM | TO — click a link to make your move |",
             "| :--: | ------------------------------------ |"]
    for from_sq in sorted(moves_by_from.keys()):
        tos = sorted(moves_by_from[from_sq])
        links = " ".join(
            f"[**{to.upper()}**](https://github.com/{REPO}/issues/new?title=chess%7Cmove%7C{from_sq}{to}&body=Click+Submit+to+play!)"
            for to in tos
        )
        lines.append(f"| **{from_sq.upper()}** | {links} |")
    return "\n".join(lines)

def build_chess_section(board):
    turn = "⬜ WHITE" if board.turn == chess.WHITE else "⬛ BLACK"
    board_md = board_to_markdown(board)

    if board.is_game_over():
        result = board.result()
        return f"""### ♟️ Community Chess — Anyone Can Play!

**Game over! Result: {result}** — Thanks for playing!

{board_md}

[![Start New Game](https://img.shields.io/badge/▶_Start_New_Game-00ff88?style=for-the-badge)](https://github.com/{REPO}/issues/new?title=chess%7Cnew&body=Click+Submit+to+start+a+new+game!)
"""
    return f"""### ♟️ Community Chess — Anyone Can Play!

**{turn}'s turn** — make a move by clicking a link below, then hit **Submit new issue**. That's it!

{board_md}

{move_links(board)}

[![New Game](https://img.shields.io/badge/🔄_Reset_Game-gray?style=flat-square)](https://github.com/{REPO}/issues/new?title=chess%7Cnew&body=Click+Submit+to+reset+the+game.)
"""

react("eyes")

parts = ISSUE_TITLE.split("|")
command = parts[1].strip() if len(parts) > 1 else ""
move_uci = parts[2].strip() if len(parts) > 2 else ""

fen_path = "chess_game/board.fen"
board = chess.Board()
if os.path.exists(fen_path) and command == "move":
    with open(fen_path) as f:
        saved = f.read().strip()
    if saved:
        board = chess.Board(saved)

if command == "new":
    board = chess.Board()
    post_comment(f"@{ISSUE_USER} New game started! ♟️ White moves first.")
elif command == "move":
    try:
        move = chess.Move.from_uci(move_uci)
        if move not in board.legal_moves:
            post_comment(f"@{ISSUE_USER} ❌ Illegal move: `{move_uci}`. [Try again.](https://github.com/{REPO})")
            close_issue()
            exit(0)
        board.push(move)
        post_comment(f"@{ISSUE_USER} ✅ Move `{move_uci}` played! [View the board.](https://github.com/{REPO})")
    except Exception:
        post_comment(f"@{ISSUE_USER} ❌ Invalid move format: `{move_uci}`.")
        close_issue()
        exit(0)
else:
    post_comment(f"@{ISSUE_USER} Unknown command. Use `chess|move|e2e4` or `chess|new`.")
    close_issue()
    exit(0)

with open(fen_path, "w") as f:
    f.write(board.fen())

chess_section = build_chess_section(board)

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
