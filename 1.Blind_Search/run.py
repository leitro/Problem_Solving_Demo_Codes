import argparse
import colorsys
import json
import importlib
from numbers import Integral
import multiprocessing as mp
import os
import textwrap
import time

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
import numpy as np

from engine import ROOT, START, GOAL, assess, failure, save_report

WIDTH, HEIGHT, CELL = 1400, 980, 16
RED, BLUE = (232, 145, 151), (30, 112, 210)


def worker(connection, level, module):
    began = time.perf_counter()
    try:
        solve = importlib.import_module(module).solve
        grid = np.array(level['grid'], dtype=np.int8)
        began = time.perf_counter()
        output = solve(grid, START, GOAL)
        elapsed = time.perf_counter() - began
        if not isinstance(output, (tuple, list)) or len(output) not in (2, 3):
            raise ValueError('Return (path, expanded, exploration)')
        result = assess(level, output[:2])
        exploration = output[2] if len(output) == 3 else []
        if not isinstance(exploration, (list, tuple, np.ndarray)) or len(exploration) > 100000:
            raise ValueError('exploration must be a sequence of at most 100000 cells')
        history = []
        for point in exploration:
            if len(point) != 2 or any(isinstance(v, bool) or not isinstance(v, Integral) for v in point):
                raise ValueError('exploration cells must contain two integers')
            r, c = map(int, point)
            if not (0 <= r < 50 and 0 <= c < 50) or level['grid'][r][c]:
                raise ValueError('exploration contains an obstacle or out-of-bounds cell')
            history.append((r, c))
        result.update(exploration=history, seconds=elapsed)
    except BaseException as error:
        result = failure(f'{type(error).__name__}: {error}', time.perf_counter() - began)
        result['exploration'] = []
    try:
        connection.send(result)
    finally:
        connection.close()


class Game:
    def __init__(self, timeout=10):
        pygame.init()
        info = pygame.display.Info()
        size = (min(WIDTH, max(640, info.current_w - 60)), min(HEIGHT, max(480, info.current_h - 80)))
        self.window = pygame.display.set_mode(size, pygame.RESIZABLE)
        pygame.display.set_caption('Blind Search | 20 Maze Challenge')
        self.screen = pygame.Surface((WIDTH, HEIGHT))
        self.font = pygame.font.SysFont('dejavusans', 21)
        self.small = pygame.font.SysFont('dejavusansmono', 18)
        self.title = pygame.font.SysFont('dejavusans', 32, bold=True)
        self.clock = pygame.time.Clock()
        data = json.loads((ROOT / 'mazes.json').read_text(encoding='utf-8'))
        self.levels, self.seed = data['levels'], data['seed']
        self.target = ROOT / 'algorithm_score.txt'
        self.timeout = timeout
        self.results, self.index, self.visible = [], 0, 0
        self.state, self.process, self.connection = 'ready', None, None
        self.save_error, self.running = '', True
        self.buttons = {'Continue': pygame.Rect(1000, 916, 180, 48), 'Exit': pygame.Rect(1196, 916, 180, 48)}
        self.build_board()

    def text(self, message, x, y, font=None, color=(30, 40, 54)):
        self.screen.blit((font or self.font).render(str(message), True, color), (x, y))

    def build_board(self):
        hue = (self.index + 2) / 22
        bg = (255, 255, 255) if self.index == 0 else tuple(round(v * 255) for v in colorsys.hsv_to_rgb(hue, 0.13, 1))
        dark = (24, 27, 35) if self.index == 0 else tuple(round(v * 255) for v in colorsys.hsv_to_rgb((hue + 0.57) % 1, 0.65, 0.24))
        self.board = pygame.Surface((800, 800))
        self.board.fill(bg)
        for r, row in enumerate(self.levels[self.index]['grid']):
            for c, cell in enumerate(row):
                if cell:
                    pygame.draw.rect(self.board, dark, (c * CELL, r * CELL, CELL, CELL))
        self.trace = pygame.Surface((800, 800), pygame.SRCALPHA)
        self.solution = pygame.Surface((800, 800), pygame.SRCALPHA)
        self.painted, self.route = 0, []

    def start(self):
        context = mp.get_context('spawn')
        self.connection, child = context.Pipe(duplex=False)
        self.process = context.Process(target=worker, args=(child, self.levels[self.index], 'algorithm'), daemon=True)
        self.process.start()
        child.close()
        self.began, self.state = time.perf_counter(), 'searching'

    def stop_worker(self):
        if self.process is not None:
            if self.process.is_alive():
                self.process.terminate()
            self.process.join(timeout=0.2)
            if self.process.is_alive():
                self.process.kill()
                self.process.join(timeout=0.2)
            self.process = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def persist(self):
        try:
            save_report(self.results, self.levels, self.seed, 'algorithm', self.target)
            self.save_error = ''
        except OSError as error:
            self.save_error = f'Save failed: {error}'

    def finish(self, result):
        self.stop_worker()
        result.setdefault('exploration', [])
        self.results.append(result)
        self.visible = 1
        self.route = result['path']
        if len(self.route) > 1:
            pygame.draw.lines(self.solution, BLUE, False, [self.center(p) for p in self.route], 4)
        self.state = 'animating' if result['exploration'] else 'review'
        self.persist()

    def center(self, point):
        return point[1] * CELL + CELL // 2, point[0] * CELL + CELL // 2

    def paint_trace(self):
        history = self.results[-1]['exploration']
        limit = min(int(self.visible), len(history))
        for r, c in history[self.painted:limit]:
            x, y = c * CELL + 3, r * CELL + 3
            pygame.draw.rect(self.trace, (*RED, 55), (x, y, 10, 10))
            for offset in (0, 7):
                pygame.draw.line(self.trace, RED, (x + offset, y), (x + offset + 3, y), 2)
                pygame.draw.line(self.trace, RED, (x + offset, y + 10), (x + offset + 3, y + 10), 2)
                pygame.draw.line(self.trace, RED, (x, y + offset), (x, y + offset + 3), 2)
                pygame.draw.line(self.trace, RED, (x + 10, y + offset), (x + 10, y + offset + 3), 2)
        self.painted = limit

    def update(self, dt):
        if self.state == 'searching':
            if self.connection.poll():
                try:
                    result = self.connection.recv()
                except (EOFError, OSError):
                    result = failure('Worker exited without a result')
                self.finish(result)
            elif time.perf_counter() - self.began > self.timeout:
                self.finish(failure(f'Timeout ({self.timeout:g}s)', self.timeout))
            elif not self.process.is_alive():
                self.finish(failure('Worker exited without a result'))
        if self.state == 'animating':
            self.visible += dt * 120
            self.paint_trace()
            if self.visible >= len(self.results[-1]['exploration']):
                self.state = 'review'

    def advance(self):
        if self.state == 'ready':
            self.start()
        elif self.state == 'animating':
            self.visible = len(self.results[-1]['exploration'])
            self.paint_trace()
            self.state = 'review'
        elif self.state == 'review':
            if self.index == len(self.levels) - 1:
                self.state = 'final'
            else:
                self.index += 1
                self.visible = 0
                self.build_board()
                self.start()

    def viewport(self):
        w, h = self.window.get_size()
        scale = min(w / WIDTH, h / HEIGHT)
        width, height = round(WIDTH * scale), round(HEIGHT * scale)
        return pygame.Rect((w - width) // 2, (h - height) // 2, width, height)

    def mouse_position(self, position):
        view = self.viewport()
        return ((position[0] - view.x) * WIDTH / view.width, (position[1] - view.y) * HEIGHT / view.height)

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            position = self.mouse_position(event.pos)
            if self.buttons['Exit'].collidepoint(position):
                self.running = False
            elif self.buttons['Continue'].collidepoint(position):
                if self.state == 'final' and self.save_error:
                    self.persist()
                else:
                    self.advance()

    def draw_buttons(self):
        mouse = self.mouse_position(pygame.mouse.get_pos())
        for label, rect in self.buttons.items():
            enabled = label == 'Exit' or self.state not in ('searching', 'final') or self.state == 'final' and bool(self.save_error)
            color = (39, 98, 177) if label == 'Continue' else (73, 82, 97)
            if not enabled:
                color = (166, 177, 192)
            elif rect.collidepoint(mouse):
                color = tuple(min(v + 20, 255) for v in color)
            pygame.draw.rect(self.screen, color, rect, border_radius=9)
            text = self.font.render(label, True, (255, 255, 255))
            self.screen.blit(text, text.get_rect(center=rect.center))

    def draw(self):
        self.screen.fill((241, 244, 248))
        self.text('BLIND SEARCH', 24, 14, self.title)
        self.text(f'20 mazes / 50 x 50 / seed {self.seed}', 24, 55)
        if self.state == 'final':
            self.draw_final()
        else:
            self.screen.blit(self.board, (24, 94))
            self.screen.blit(self.trace, (24, 94))
            if self.state == 'review':
                self.screen.blit(self.solution, (24, 94))
            if self.state == 'animating':
                history = self.results[-1]['exploration']
                p = history[min(int(self.visible), len(history)) - 1]
                x, y = self.center(p)
                pygame.draw.circle(self.screen, (224, 149, 24), (24 + x, 94 + y), 6)
            for p, color in ((START, (0, 133, 80)), (GOAL, (205, 45, 70))):
                pygame.draw.rect(self.screen, color, (24 + p[1] * CELL, 94 + p[0] * CELL, CELL, CELL))
            self.draw_panel()
        self.draw_buttons()
        self.window.fill((30, 40, 54))
        view = self.viewport()
        self.window.blit(pygame.transform.smoothscale(self.screen, view.size), view)
        pygame.display.flip()

    def draw_panel(self):
        level = self.levels[self.index]
        self.text(f'Level {self.index + 1:02} / 20', 856, 96, self.title)
        lines = [f'Obstacles: {level["obstacles"]} / 2500',
                 f'Shortest route: {level["optimal"]} moves',
                 'Green: start / Red: goal',
                 'Light-red cells: exploration history',
                 'Blue line: final route', '',
                 f'Overall: {sum(r["score"] for r in self.results)/20:.2f} / 100']
        if self.state in ('review', 'animating'):
            r = self.results[-1]
            lines += ['', f'Path moves: {r["moves"] if r["moves"] is not None else "--"}',
                      f'Level score: {r["score"]:.2f} / 100',
                      f'Expanded: {r["expanded"] if r["expanded"] is not None else "--"}',
                      f'Search time: {r["seconds"]*1000:.2f} ms']
            if self.state == 'animating':
                lines += [f'Exploration: {min(int(self.visible), len(r["exploration"]))} / {len(r["exploration"])} cells']
            elif self.route:
                lines += [f'Blue route: {len(self.route)-1} moves',
                          'Score uses the returned path only.']
            lines += [''] + textwrap.wrap(r['status'], 42)[:4]
        elif self.state == 'searching':
            lines += ['', 'Running algorithm.py...', f'Time limit: {self.timeout:g} seconds']
        else:
            lines += ['', 'Click Continue to start algorithm.py.']
        for n, line in enumerate(lines):
            self.text(line, 856, 148 + n * 31)
        if self.save_error:
            for n, line in enumerate(textwrap.wrap(self.save_error, 43)[:3]):
                self.text(line, 856, 802 + n * 26, color=(170, 30, 30))
        hint = {'ready': 'Continue: start level 1', 'searching': 'Searching... Exit remains available.',
                'animating': 'Continue: finish animation and reveal solution',
                'review': 'Continue: final statistics' if self.index == 19 else 'Continue: next level'}[self.state]
        self.text(hint, 24, 929)

    def draw_final(self):
        score = sum(r['score'] for r in self.results) / 20
        solved = sum(r['status'] == 'Solved' for r in self.results)
        self.text(f'Overall score  {score:.2f} / 100', 24, 96, self.title)
        self.text(f'Solved {solved}/20   |   Total moves {sum(r["moves"] or 0 for r in self.results)}   |   Search {sum(r["seconds"] for r in self.results):.3f}s', 24, 143)
        self.text('LEVEL    MOVES   OPTIMAL   EXPANDED   TIME(ms)   SCORE   RESULT', 24, 189, self.small)
        for i, (level, r) in enumerate(zip(self.levels, self.results)):
            moves = '--' if r['moves'] is None else str(r['moves'])
            expanded = '--' if r['expanded'] is None else str(r['expanded'])
            line = f'{i+1:02}     {moves:>6}    {level["optimal"]:>6}   {expanded:>8}   {1000*r["seconds"]:>8.2f}  {r["score"]:>6.2f}   {r["status"][:42]}'
            self.text(line, 24, 226 + i * 29, self.small)
        if self.save_error:
            self.text('Report not saved. Click Continue to retry.', 24, 848, color=(170, 30, 30))
            self.text(self.save_error[:105], 24, 877, self.small, (170, 30, 30))
        else:
            self.text('Saved: algorithm_score.txt', 24, 848)
        self.text('All levels finished. Click Exit to close.', 24, 929)

    def run(self):
        try:
            while self.running:
                dt = self.clock.tick(60) / 1000
                for event in pygame.event.get():
                    self.handle_event(event)
                if not self.running:
                    break
                self.update(dt)
                self.draw()
        finally:
            self.stop_worker()
            if self.results:
                self.persist()
                if self.save_error:
                    print(self.save_error)
            pygame.quit()


if __name__ == '__main__':
    mp.freeze_support()
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeout', type=float, default=10)
    args = parser.parse_args()
    if not 0 < args.timeout < float('inf'):
        parser.error('--timeout must be positive and finite')
    Game(args.timeout).run()
