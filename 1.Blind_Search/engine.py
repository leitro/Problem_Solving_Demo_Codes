import importlib
import json
import random
import time
from collections import deque
from numbers import Integral
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
START, GOAL = (1, 1), (48, 48)
SEED = 2026


def reference(grid, start=START, goal=GOAL):
    queue, parents = deque([start]), {start: None}
    expanded = 0
    while queue:
        p = queue.popleft()
        expanded += 1
        if p == goal:
            path = []
            while p is not None:
                path.append(p)
                p = parents[p]
            return path[::-1], expanded
        r, c = p
        for q in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= q[0] < 50 and 0 <= q[1] < 50 and not grid[q] and q not in parents:
                parents[q] = p
                queue.append(q)
    return [], expanded


def generate(seed=SEED):
    rng, candidates = random.Random(seed), {}
    for i in range(24):
        for attempt in range(10):
            grid = np.array([[int(rng.random() < 0.06 + i * 0.006) for _ in range(50)] for _ in range(50)])
            grid[0, :] = grid[-1, :] = 1
            grid[:, 0] = grid[:, -1] = 1
            rows = [round(3 + k * 43 / max(1, i - 1)) for k in range(i)]
            r, c = START
            grid[r, c] = 0
            for k, wall in enumerate(rows):
                gap = rng.randint(44, 48) if k % 2 == 0 else rng.randint(1, 5)
                grid[r:wall, c] = 0
                r = wall - 1
                grid[r, min(c, gap):max(c, gap) + 1] = 0
                grid[wall, :] = 1
                grid[wall:wall + 2, gap] = 0
                r, c = wall + 1, gap
            grid[r:49, c] = 0
            grid[48, min(c, 48):49] = 0
            path, expanded = reference(grid)
            optimum = len(path) - 1
            if path:
                candidates[optimum] = dict(grid=grid.tolist(), optimal=optimum,
                                          baseline_expanded=expanded, obstacles=int(grid.sum()))
    ordered = [candidates[k] for k in sorted(candidates)]
    if len(ordered) < 20:
        raise RuntimeError('Not enough distinct difficulties; try another seed.')
    levels = [dict(ordered[round(i * (len(ordered) - 1) / 19)], level=i + 1) for i in range(20)]
    return dict(seed=seed, levels=levels)


def assess(level, output):
    path, expanded = output
    if expanded is not None and (isinstance(expanded, bool) or not isinstance(expanded, Integral) or expanded < 0):
        raise ValueError('expanded must be a nonnegative integer or None')
    if not isinstance(path, (list, tuple, np.ndarray)) or len(path) > 100000:
        raise ValueError('path must be a sequence of at most 100000 positions')
    clean = []
    for p in path:
        if len(p) != 2 or any(isinstance(v, bool) or not isinstance(v, Integral) for v in p):
            raise ValueError('positions must contain two integers')
        r, c = map(int, p)
        if not (0 <= r < 50 and 0 <= c < 50) or level['grid'][r][c]:
            raise ValueError('path leaves the grid or crosses an obstacle')
        if clean and abs(r - clean[-1][0]) + abs(c - clean[-1][1]) != 1:
            raise ValueError('each move must be one orthogonal step')
        clean.append((r, c))
    if clean and (clean[0] != START or clean[-1] != GOAL):
        raise ValueError('path must begin at start and end at goal')
    moves = len(clean) - 1 if clean else None
    return dict(path=clean, expanded=None if expanded is None else int(expanded),
                moves=moves, score=100 * level['optimal'] / moves if clean else 0,
                status='Solved' if clean else 'No path returned')


def worker(connection, level, module):
    began = time.perf_counter()
    try:
        solve = importlib.import_module(module).solve
        grid = np.array(level['grid'], dtype=np.int8)
        began = time.perf_counter()
        output = solve(grid, START, GOAL)
        elapsed = time.perf_counter() - began
        result = assess(level, output)
        result['seconds'] = elapsed
    except BaseException as error:
        result = failure(f'{type(error).__name__}: {error}', time.perf_counter() - began)
    try:
        connection.send(result)
    finally:
        connection.close()


def failure(message, seconds=0):
    return dict(path=[], expanded=None, moves=None, score=0, status=message, seconds=seconds)


def save_report(results, levels, seed, module, target):
    lines = [f'BLIND SEARCH LAB | seed={seed} | algorithm={module}',
             f'Attempted: {len(results)}/20 | Solved: {sum(r["status"] == "Solved" for r in results)}/20',
             f'Overall score: {sum(r["score"] for r in results) / 20:.2f}/100',
             'Unattempted levels count as zero. Moves exclude the start cell.',
             'Expanded = student-reported frontier removals, including goal; not graded.',
             'Level | Moves | Optimal | Expanded | BFS expanded | Search ms | Score | Status']
    for level, r in zip(levels, results):
        lines.append(f'{level["level"]:02} | {r["moves"]} | {level["optimal"]} | {r["expanded"]} | '
                     f'{level["baseline_expanded"]} | {1000*r["seconds"]:.3f} | {r["score"]:.2f} | {r["status"]}')
    lines += [f'Total successful moves: {sum(r["moves"] or 0 for r in results)}',
              f'Total recorded search time: {sum(r["seconds"] for r in results):.6f} seconds']
    target = Path(target)
    temp = target.with_suffix('.tmp')
    temp.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    temp.replace(target)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=SEED)
    args = parser.parse_args()
    (ROOT / 'mazes.json').write_text(json.dumps(generate(args.seed)), encoding='utf-8')
