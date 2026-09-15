# Problem Solving Demo Codes

**Implement classic AI algorithms. Visualize their behaviour. Learn through experiments.**

A **Pygame-based frameworks** for the **Problem Solving practical sessions of a second-year Bachelor's degree in Artificial Intelligence**.

The aim is to provide a visual environment in which to implement, test, and compare classic algorithms. The frameworks provide the environment and visualization so students can focus on how their algorithms represent problems, explore possibilities, and make decisions.

The practical series begins with blind search and will expand to heuristic search, game search, and further problem-solving topics. New practicals and improvements will be added over time.

## Practical series

| Part | Topic | Main algorithms and concepts | Status |
| --- | --- | --- | --- |
| 1 | Blind Search: 20 Maze Challenge | Breadth-first search, depth-first search, path reconstruction, search effort | Documented below |
| 2 | A* Search | Heuristics, path cost, priority queues, informed search | Planned; implementation and launch details to follow |
| 3 | Game Search | Minimax, evaluation functions, depth limits, alpha–beta pruning | Planned; implementation and launch details to follow |

## Learning goals

By working through these practicals, students should be able to:

- Define states, actions, transitions, and goals for a search problem.
- Implement classic search algorithms using appropriate data structures.
- Reconstruct and validate a solution path or select a legal game action.
- Explain the difference between solution quality and computational effort.
- Use visual observations and measured results to compare algorithms.
- Explain how heuristics, search depth, and problem structure affect performance.

## Requirements

- **Python 3.10 or later**, and required packages in requirements.txt. 

  ```bash
  python -m pip install -r requirements.txt
  ```

- A desktop or laptop with a **graphical display** for normal Pygame use.
- Basic Python knowledge: functions, lists, dictionaries, sets, and loops.
- Familiarity with the relevant search concepts from theory class.

## Getting started

1. Download this repository using **Code → Download ZIP** and extract it, or clone it:

   ```bash
   git clone https://github.com/leitro/Problem_Solving_Demo_Codes.git
   cd Problem_Solving_Demo_Codes
   ```

2. Open the practical you want to work on. 
3. Follow that practical's setup instructions. Run commands from its own folder, where its requirements and launcher are located.
4. Read the provided algorithm interface before making changes. Preserve the expected function signature and return format.
5. Implement your algorithm, launch the application, and inspect its behaviour and results.


## 1. Blind Search: 20 Maze Challenge

Implement a search algorithm and test it on **20 fixed mazes**. Compare the length of the path it returns with the true shortest path, and examine how much search effort was needed to find it.

### Start

Open a terminal in the folder containing `run.py`:

Edit `algorithm.py` before launching. The supplied algorithm is a **random-search demonstration**; replace it with your own implementation while keeping the required interface.

Launch the application:

```bash
python run.py
```

### Key files

| File | Purpose |
| --- | --- |
| `algorithm.py` | Student algorithm implementation; the supplied version demonstrates random search. |
| `run.py` | Application launcher. |
| `mazes.json` | The 20 fixed maze grids and their metadata. |
| `engine.py` | Includes the command for generating a reproducible maze set. |
| `algorithm_score.txt` | Generated results report. |

### Scoring

For a valid completed path:

**Level score = 100 × optimal moves / submitted moves**

Failure, malformed output, an invalid path, a crash, or a timeout earns **0**.

**Overall score = sum of level scores / 20**

Each level has equal weight. Unattempted levels count as zero in a partial report.

| Result | Level score |
| --- | --- |
| A shortest path | 100 |
| A valid path twice as long as the shortest path | 50 |
| A valid path four times as long as the shortest path | 25 |
| Failure or invalid result | 0 |

**Moves = `len(path) - 1`.** Moves are not the number of nodes explored. A search algorithm may explore many nodes before returning a short path.

This scoring adapts **Success weighted by Path Length (SPL)**, used in the [Habitat Navigation Challenge](https://aihabitat.org/challenge/2023/), to exact-goal, unit-cost grid navigation. Valid paths cannot be shorter than the optimal path, so the usual `max(optimal, actual)` denominator simplifies to actual moves.

The score measures successful path quality. Use the expansion and timing results separately to discuss search efficiency.

### Results report

`algorithm_score.txt` is created beside `run.py` after each result and again on exit. It contains:

- Every attempted level, including failures.
- Submitted moves and optimal moves.
- Expanded nodes and reference expansions.
- Timing, level scores, and totals.
- The seed and algorithm module.

Each run replaces the report once its first result is obtained. **Rename or copy a previous report before starting another run if you want to keep it.** A partial run is saved but cannot be resumed.

### Maze design and reproducibility

`mazes.json` contains all **20 fixed 50 × 50 grids**, so all students face exactly the same challenge when using the supplied file.

For **seed 2026**, the shortest route lengths, in moves, are:

```text
94, 186, 270, 350, 418, 442, 516, 540, 610, 632,
694, 758, 786, 846, 874, 924, 946, 964, 1018, 1048
```

The generator combines random obstacles with alternating-gap barriers and carves a guaranteed route. It builds **240 candidates**, computes their true shortest paths using BFS, and selects **20 distinct, strictly increasing path lengths**.

This avoids unsolvable random grids and gives an objective progression in required travel. Obstacle count and expansion count need not increase at every level: algorithm-specific difficulty also depends on maze topology and neighbour order.

To replace the supplied set with another reproducible set:

```bash
python engine.py --seed 2027
```

**This overwrites `mazes.json`.** Use the same seed and maze file for comparisons. Do not change the grids, metadata, or grading code during a scored exercise.

### Suggested practical

1. Implement **breadth-first search (BFS)** and reconstruct a path through parent pointers.
2. Add a frontier-removal counter. State exactly what it counts and explain the difference between moves and search effort.
3. Implement **depth-first search (DFS)**, run the same mazes, and compare path quality and expansions.
4. Explain why BFS returns a shortest path in this unit-cost setting and why DFS may return a longer path.
5. Explain why obstacle density alone does not determine search difficulty.

## 2. A* Search

