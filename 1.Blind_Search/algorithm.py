import random

"""Return (path, expanded, exploration): path includes start and goal; expanded counts visited nodes.

grid: NumPy array, grid[row, column], 0 = free, 1 = obstacle.
start, goal: (row, column). Only up/down/left/right moves are allowed.
Return ([], expanded, exploration) when no path exists.

Replace the random search demo with BFS and DFS and compare.
"""
def solve(grid, start, goal):
    # random search demo starts
    frontier = [start]
    parent = {start: None}
    expanded = 0
    exploration = []

    while frontier:
        # Random Search: randomly select and remove a node from the frontier
        idx = random.randrange(len(frontier))
        current = frontier.pop(idx)
        
        expanded += 1
        exploration.append(current)

        if current == goal:
            path = []
            while current is not None:
                path.append(current)
                current = parent[current]
            return path[::-1], expanded, exploration

        r, c = current
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            neighbor = (r + dr, c + dc)
            nr, nc = neighbor
            if 0 <= nr < grid.shape[0] and 0 <= nc < grid.shape[1] and grid[neighbor] == 0 and neighbor not in parent:
                parent[neighbor] = current
                frontier.append(neighbor)

    # random search demo ends
    return [], expanded, exploration
