# citadel/workflows/tic_tac_toe.py
"""Single-player Tic-Tac-Toe against a simple rule-based opponent (win
if possible, else block, else center, else corner, else edge -- no
minimax, no LLM: deterministic game logic doesn't need either, and a
"perfect" minimax opponent would make the game unwinnable, which isn't
much fun for a casual BBS game).

The board lives entirely in the workflow's in-memory wf_state.data for
the session -- no DB table needed, unlike trivia's day-spanning state.
"""

import random

from citadel.transport.packets import ToUser
from citadel.workflows.base import Workflow, WorkflowState
from citadel.workflows.registry import register

WIN_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),  # columns
    (0, 4, 8), (2, 4, 6),             # diagonals
]
CORNERS = [0, 2, 6, 8]
EDGES = [1, 3, 5, 7]


def _render_board(board) -> str:
    cells = [board[i] if board[i] else str(i + 1) for i in range(9)]
    return (
        f"|{cells[0]}|{cells[1]}|{cells[2]}|\n"
        f"|{cells[3]}|{cells[4]}|{cells[5]}|\n"
        f"|{cells[6]}|{cells[7]}|{cells[8]}|"
    )


def _check_winner(board):
    """Returns 'x', 'o', 'draw', or None (game still in progress)."""
    for a, b, c in WIN_LINES:
        if board[a] is not None and board[a] == board[b] == board[c]:
            return board[a]
    if all(cell is not None for cell in board):
        return "draw"
    return None


def _find_winning_move(board, symbol):
    for idx in (i for i, v in enumerate(board) if v is None):
        trial = board.copy()
        trial[idx] = symbol
        if _check_winner(trial) == symbol:
            return idx
    return None


def _choose_ai_move(board) -> int:
    win = _find_winning_move(board, "o")
    if win is not None:
        return win
    block = _find_winning_move(board, "x")
    if block is not None:
        return block
    if board[4] is None:
        return 4
    free_corners = [c for c in CORNERS if board[c] is None]
    if free_corners:
        return random.choice(free_corners)
    free_edges = [e for e in EDGES if board[e] is None]
    return random.choice(free_edges)


@register
class TicTacToeWorkflow(Workflow):
    kind = "tic_tac_toe"

    async def start(self, context):
        board = [None] * 9
        data = {"board": board}
        context.session_mgr.set_workflow(
            context.session_id,
            WorkflowState(kind=self.kind, step=2, data=data)
        )
        return ToUser(
            session_id=context.session_id,
            text=("Tic-Tac-Toe! You're X, the BBS is O.\n"
                  f"{_render_board(board)}\nPick a cell (1-9):"),
            hints={"type": "text", "workflow": self.kind, "step": 2}
        )

    async def handle(self, context, command):
        step = context.wf_state.step
        data = context.wf_state.data

        if step == 2:
            board = data["board"]
            choice = (command or "").strip()

            if not choice.isdigit() or not (1 <= int(choice) <= 9):
                return ToUser(
                    session_id=context.session_id,
                    text=f"Please pick a number 1-9.\n{_render_board(board)}",
                    is_error=True,
                    error_code="invalid_cell",
                    hints={"type": "text", "workflow": self.kind, "step": 2}
                )

            idx = int(choice) - 1
            if board[idx] is not None:
                return ToUser(
                    session_id=context.session_id,
                    text=f"That cell's taken. Pick another.\n{_render_board(board)}",
                    is_error=True,
                    error_code="cell_taken",
                    hints={"type": "text", "workflow": self.kind, "step": 2}
                )

            board[idx] = "x"
            winner = _check_winner(board)
            if winner:
                context.session_mgr.clear_workflow(context.session_id)
                return ToUser(session_id=context.session_id, text=self._end_message(board, winner))

            ai_idx = _choose_ai_move(board)
            board[ai_idx] = "o"
            winner = _check_winner(board)
            if winner:
                context.session_mgr.clear_workflow(context.session_id)
                return ToUser(session_id=context.session_id, text=self._end_message(board, winner))

            context.session_mgr.set_workflow(
                context.session_id,
                WorkflowState(kind=self.kind, step=2, data=data)
            )
            return ToUser(
                session_id=context.session_id,
                text=f"{_render_board(board)}\nYour move (1-9):",
                hints={"type": "text", "workflow": self.kind, "step": 2}
            )

        return ToUser(
            session_id=context.session_id,
            text=f"Invalid tic-tac-toe step: {step}",
            is_error=True,
            error_code="invalid_step"
        )

    def _end_message(self, board, winner) -> str:
        if winner == "draw":
            result = "It's a draw!"
        elif winner == "x":
            result = "You win!"
        else:
            result = "The BBS wins!"
        return f"{_render_board(board)}\n{result}"

    async def cleanup(self, context):
        """Nothing to clean up -- the board lives only in wf_state.data,
        no DB writes happen mid-game."""
        pass
