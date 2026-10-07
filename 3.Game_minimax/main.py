import importlib.util
import json
import queue
import threading
import time
import traceback
from pathlib import Path

import chess
import pygame


ROOT = Path(__file__).resolve().parent
LIGHT = (231, 225, 211)
DARK = (111, 139, 127)
BACKGROUND = (25, 33, 40)
TEXT = (230, 235, 237)
ACCENT = (238, 188, 83)


def load_config(path=ROOT / "config.json"):
    config = json.loads(Path(path).read_text())
    if config["mode"] not in ("human_vs_ai", "ai_vs_ai"):
        raise ValueError("mode must be human_vs_ai or ai_vs_ai.")
    if config["human_color"] not in ("white", "black"):
        raise ValueError("human_color must be white or black.")
    depth = config["search_depth"]
    if type(depth) is not int or depth < 1:
        raise ValueError("search_depth must be a positive integer.")
    for key in ("white_algorithm", "black_algorithm"):
        if not isinstance(config[key], str) or not config[key].endswith(".py"):
            raise ValueError(f"{key} must name a Python file.")
    board = chess.Board(config["initial_fen"])
    if not board.is_valid():
        raise ValueError("initial_fen must be a valid chess position.")
    return config


def load_algorithm(filename):
    path = ROOT / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "choose_move", None)):
        raise ValueError(f"{filename} must define choose_move(board, depth).")
    return module


class ChessGame:
    def __init__(self, config=None):
        self.config = load_config() if config is None else config
        self.initial_fen = self.config["initial_fen"]
        self.board = chess.Board(self.initial_fen)
        self.human = (self.config["human_color"] == "white"
                      if self.config["mode"] == "human_vs_ai" else None)
        self.depth = self.config["search_depth"]
        self.algorithms = {
            color: load_algorithm(self.config[f'{"white" if color else "black"}_algorithm'])
            for color in chess.COLORS if color != self.human
        }
        self.selected = None
        self.promotion_moves = []
        self.thinking = False
        self.failed = False
        self.claimed_draw = False
        self.results = queue.Queue()
        self.notice = ""
        self.last_time = None
        self.last_move = "-"
        self.screen = pygame.display.set_mode((800, 880), pygame.RESIZABLE)
        pygame.display.set_caption("Chess Lab")
        self.original_images = {}
        for color in chess.COLORS:
            for kind in chess.PIECE_TYPES:
                name = f'{"white" if color else "black"}_{chess.piece_name(kind)}.svg'
                self.original_images[color, kind] = pygame.image.load(ROOT / "assets" / name)
        self.resize(self.screen.get_size())

    def resize(self, size):
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        width, height = self.screen.get_size()
        self.cell = max(1, min(width // 8, max(8, height - 88) // 8))
        self.board_rect = pygame.Rect((width - self.cell * 8) // 2, 44,
                                      self.cell * 8, self.cell * 8)
        self.font = pygame.font.Font(None, max(12, min(24, width // 28)))
        self.small = pygame.font.Font(None, max(10, min(19, width // 35)))
        piece_size = max(1, int(self.cell * 0.88))
        self.images = {key: pygame.transform.smoothscale(image, (piece_size, piece_size))
                       for key, image in self.original_images.items()}

    def finished(self):
        return self.claimed_draw or self.board.is_game_over(claim_draw=False)

    def square_at(self, position):
        if not self.board_rect.collidepoint(position):
            return None
        file = (position[0] - self.board_rect.x) // self.cell
        rank = 7 - (position[1] - self.board_rect.y) // self.cell
        if self.human == chess.BLACK:
            file, rank = 7 - file, 7 - rank
        return chess.square(file, rank)

    def rect_for(self, square):
        file, rank = chess.square_file(square), chess.square_rank(square)
        if self.human == chess.BLACK:
            file, rank = 7 - file, 7 - rank
        return pygame.Rect(self.board_rect.x + file * self.cell,
                           self.board_rect.y + (7 - rank) * self.cell,
                           self.cell, self.cell)

    def play(self, move):
        self.last_move = self.board.san(move)
        self.board.push(move)
        self.selected = None
        self.promotion_moves = []
        self.notice = ""

    def handle_click(self, position):
        if self.thinking or self.failed or self.finished() or self.board.turn != self.human:
            return
        if self.promotion_moves:
            for index, kind in enumerate((chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)):
                if self.promotion_rect(index).collidepoint(position):
                    self.promote(kind)
            return
        square = self.square_at(position)
        if square is None:
            return
        if self.selected is not None:
            candidates = [move for move in self.board.legal_moves
                          if move.from_square == self.selected and move.to_square == square]
            if candidates:
                if candidates[0].promotion:
                    self.promotion_moves = candidates
                else:
                    self.play(candidates[0])
                return
        piece = self.board.piece_at(square)
        self.selected = square if piece and piece.color == self.human else None

    def promote(self, kind):
        for move in self.promotion_moves:
            if move.promotion == kind:
                self.play(move)
                return

    def handle_key(self, key):
        if self.thinking:
            return
        if self.promotion_moves:
            choices = {pygame.K_q: chess.QUEEN, pygame.K_r: chess.ROOK,
                       pygame.K_b: chess.BISHOP, pygame.K_n: chess.KNIGHT}
            if key in choices:
                self.promote(choices[key])
            elif key == pygame.K_ESCAPE:
                self.promotion_moves = []
            return
        if key == pygame.K_r:
            self.board = chess.Board(self.initial_fen)
            self.selected = None
            self.failed = self.claimed_draw = False
            self.last_move = "-"
            self.last_time = None
            self.notice = "New game."
        elif key == pygame.K_u and self.board.move_stack:
            self.board.pop()
            if self.human is not None and self.board.turn != self.human and self.board.move_stack:
                self.board.pop()
            self.selected = None
            self.failed = self.claimed_draw = False
            self.last_move = "-"
            self.last_time = None
            self.notice = "Move undone."
        elif key == pygame.K_d and self.board.turn == self.human and not self.finished():
            if self.board.can_claim_draw():
                self.claimed_draw = True
                self.notice = "Draw claimed."
            else:
                self.notice = "No draw claim available."

    def start_ai(self):
        if self.thinking or self.failed or self.finished() or self.board.turn == self.human:
            return
        self.thinking = True
        self.notice = "AI is searching..."
        board_copy = self.board.copy(stack=True)
        algorithm = self.algorithms[self.board.turn]

        def worker():
            start = time.perf_counter()
            try:
                move = algorithm.choose_move(board_copy, self.depth)
                self.results.put((move, time.perf_counter() - start, None))
            except Exception as error:
                traceback.print_exc()
                self.results.put((None, time.perf_counter() - start, str(error)))

        threading.Thread(target=worker, daemon=True).start()

    def collect_ai(self):
        try:
            move, elapsed, error = self.results.get_nowait()
        except queue.Empty:
            return
        self.thinking = False
        self.last_time = elapsed
        if error is not None:
            self.failed = True
            self.notice = "Algorithm error; see terminal."
        elif not isinstance(move, chess.Move) or move not in self.board.legal_moves:
            self.failed = True
            self.notice = "AI must return a legal move; complete its choose_move function."
        else:
            self.play(move)

    def promotion_rect(self, index):
        size = self.cell
        return pygame.Rect(self.board_rect.centerx - 2 * size + index * size,
                           self.board_rect.centery, size, size)

    def status(self):
        outcome = self.board.outcome(claim_draw=False)
        if self.claimed_draw:
            return "Draw claimed"
        if outcome:
            return {"1-0": "White wins", "0-1": "Black wins", "1/2-1/2": "Draw"}[outcome.result()]
        status = f'{"White" if self.board.turn else "Black"} to move'
        if self.board.is_check():
            status += " | Check"
        return status

    def draw_text(self, text, font, color, y):
        image = font.render(text, True, color)
        width = self.screen.get_width() - 12
        if width > 0 and image.get_width() > width:
            image = pygame.transform.smoothscale(image, (width, image.get_height()))
        self.screen.blit(image, image.get_rect(centerx=self.screen.get_width() // 2, y=y))

    def draw(self):
        self.screen.fill(BACKGROUND)
        self.draw_text(self.status(), self.font, ACCENT, 12)
        destinations = set()
        if self.selected is not None:
            destinations = {m.to_square for m in self.board.legal_moves if m.from_square == self.selected}
        last = self.board.peek() if self.board.move_stack else None
        for square in chess.SQUARES:
            rect = self.rect_for(square)
            file, rank = chess.square_file(square), chess.square_rank(square)
            color = LIGHT if (file + rank) % 2 else DARK
            pygame.draw.rect(self.screen, color, rect)
            if last and square in (last.from_square, last.to_square):
                pygame.draw.rect(self.screen, (176, 178, 104), rect)
            if square == self.selected:
                pygame.draw.rect(self.screen, ACCENT, rect, max(1, self.cell // 20))
            piece = self.board.piece_at(square)
            if piece:
                image = self.images[piece.color, piece.piece_type]
                self.screen.blit(image, image.get_rect(center=rect.center))
            if square in destinations:
                pygame.draw.circle(self.screen, (56, 86, 75), rect.center,
                                   max(2, self.cell // 10), 2 if piece else 0)
        notice = self.notice or f"Last move: {self.last_move}"
        if self.last_time is not None and not self.notice:
            notice += f"  |  AI: {self.last_time:.2f}s"
        y = self.board_rect.bottom + 5
        self.draw_text(notice, self.small, TEXT, y)
        self.draw_text("R Restart   U Undo   D Claim draw   Esc Exit", self.small, TEXT, y + 20)
        if self.promotion_moves:
            shade = pygame.Surface(self.board_rect.size, pygame.SRCALPHA)
            shade.fill((15, 20, 24, 190))
            self.screen.blit(shade, self.board_rect)
            self.draw_text("Choose a promotion: Q / R / B / N", self.font, TEXT,
                           self.board_rect.centery - 30)
            for index, kind in enumerate((chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)):
                rect = self.promotion_rect(index)
                pygame.draw.rect(self.screen, LIGHT, rect)
                image = self.images[self.board.turn, kind]
                self.screen.blit(image, image.get_rect(center=rect.center))
        pygame.display.flip()

    def run(self):
        clock = pygame.time.Clock()
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.resize(event.size)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE and not self.promotion_moves:
                        if self.selected is not None:
                            self.selected = None
                        else:
                            running = False
                    else:
                        self.handle_key(event.key)
            if not running:
                break
            self.collect_ai()
            self.start_ai()
            self.draw()
            clock.tick(30)


def main():
    config = load_config()
    pygame.init()
    try:
        ChessGame(config).run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
