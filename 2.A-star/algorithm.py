from heapq import heappop, heappush


def solve(grid, start, goal):
    # Modify the h function, monitor how the changes affect performance, and discuss the observed results.
    def heuristic(position):
        return abs(position[0] - goal[0]) + abs(position[1] - goal[1])

    frontier = [(heuristic(start), 0, start)]
    parent = {start: None}
    cost = {start: 0}
    expanded = 0
    exploration = []

    while frontier:
        _, current_cost, current = heappop(frontier)
        if current_cost != cost[current]:
            continue

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
            if 0 <= nr < grid.shape[0] and 0 <= nc < grid.shape[1] and grid[neighbor] == 0:
                new_cost = current_cost + 1
                if new_cost < cost.get(neighbor, float('inf')):
                    cost[neighbor] = new_cost
                    parent[neighbor] = current
                    heappush(frontier, (new_cost + heuristic(neighbor), new_cost, neighbor))

    return [], expanded, exploration
