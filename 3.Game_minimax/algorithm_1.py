import chess


PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}
CHECKMATE_SCORE = 100000


def evaluate_board(board: chess.Board) -> float:
    score = 0
    for piece_type, value in PIECE_VALUES.items():
        white_count = len(board.pieces(piece_type, chess.WHITE))
        black_count = len(board.pieces(piece_type, chess.BLACK))
        score += value * (white_count - black_count)
    return score


def terminal_score(board: chess.Board):
    outcome = board.outcome(claim_draw=False)
    if outcome is None:
        return None
    if outcome.winner is chess.WHITE:
        return CHECKMATE_SCORE
    if outcome.winner is chess.BLACK:
        return -CHECKMATE_SCORE
    return 0


def minimax(board: chess.Board, depth: int) -> float:
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
                child_score = minimax(board, depth - 1)
            finally:
                board.pop()
            best_score = max(best_score, child_score)
        return best_score
    best_score = float('inf')
    for move in list(board.legal_moves):
        board.push(move)
        try:
            child_score = minimax(board, depth - 1)
        finally:
            board.pop()
        best_score = min(best_score, child_score)
    return best_score


def choose_move(board: chess.Board, depth: int = 10):
    if depth < 1:
        raise ValueError('Search depth must be at least 1.')
    if terminal_score(board) is not None:
        return None
    maximizing = board.turn == chess.WHITE
    best_score = float('-inf') if maximizing else float('inf')
    best_move = None
    for move in list(board.legal_moves):
        board.push(move)
        try:
            score = minimax(board, depth - 1)
        finally:
            board.pop()
        if best_move is None or (maximizing and score > best_score) or (
            not maximizing and score < best_score
        ):
            best_score = score
            best_move = move
    return best_move
