"""
Minimax with alpha-beta pruning, using the original bot's evaluation.
Scores are always from White's perspective: White maximizes, Black minimizes.
Depth counts individual player moves (plies), including the chosen root move.
Shuffle root moves to vary equally good choices. Recursive move order and
the alpha-beta search stay unchanged.
"""

import random
import chess
from algorithm_bot import evaluate_board, terminal_score


def alpha_beta(
    board: chess.Board,
    depth: int,
    alpha: float = float('-inf'),
    beta: float = float('inf'),
) -> float:
    """
    Search a position with the bounds inherited from its ancestors.
    alpha: the lower bound established by White's alternatives so far.
    beta: the upper bound established by Black's alternatives so far.
    When alpha >= beta, remaining siblings cannot improve an ancestor's
    decision, so they can be skipped. A full window (-inf, inf) returns the
    exact minimax score; a cutoff may return only a bound on that score.
    """
    # Check endings before the depth limit, including mates at the horizon.
    result = terminal_score(board)
    if result is not None:
        return result
    if depth <= 0:
        return evaluate_board(board)

    if board.turn == chess.WHITE:
        best_score = float('-inf')
        for move in list(board.legal_moves):
            board.push(move)
            try:
                child_score = alpha_beta(board, depth - 1, alpha, beta)
            finally:
                board.pop()
            best_score = max(best_score, child_score)
            # White can already obtain at least this score.
            alpha = max(alpha, best_score)
            if alpha >= beta:
                break  # Black has an alternative that is no worse.
        return best_score

    best_score = float('inf')
    for move in list(board.legal_moves):
        board.push(move)
        try:
            child_score = alpha_beta(board, depth - 1, alpha, beta)
        finally:
            board.pop()
        best_score = min(best_score, child_score)
        # Black can already hold the score down to this value.
        beta = min(beta, best_score)
        if alpha >= beta:
            break  # White has an alternative that is no worse.
    return best_score


def choose_move(board: chess.Board, depth: int = 10):
    """Return a legal move, or None for a finished game, without changing board."""
    if depth < 1:
        raise ValueError('Search depth must be at least 1.')
    if terminal_score(board) is not None:
        return None

    maximizing = board.turn == chess.WHITE
    best_score = float('-inf') if maximizing else float('inf')
    best_move = None
    alpha, beta = float('-inf'), float('inf')

    # Randomize root order, then keep the first strictly best move found.
    # Do not randomly accept equal scores: cutoff results may be bounds.
    moves = list(board.legal_moves)
    random.shuffle(moves)

    for move in moves:
        board.push(move)
        try:
            score = alpha_beta(board, depth - 1, alpha, beta)
        finally:
            board.pop()
        # Keep the first move on a tie. Internal cutoff scores can be bounds,
        # so a later equal return is not necessarily an exact minimax tie.
        if best_move is None or (maximizing and score > best_score) or (
            not maximizing and score < best_score
        ):
            best_score = score
            best_move = move

        # Carry the root's best bound into the next sibling's search.
        # Resetting both bounds for every move would lose some pruning.
        if maximizing:
            alpha = max(alpha, best_score)
        else:
            beta = min(beta, best_score)
    return best_move
