*This project has been created as part of the 42 curriculum by nrajaoar.*

# Fly-in — Drones are interesting.

## Description

Fly-in routes a fleet of `N` drones from one **start zone** to one **end zone** of a graph of zones, in as few simulation turns as possible, while respecting:

- zone capacity (`max_drones`) and connection capacity (`max_link_capacity`);
- zone types: `normal` (1 turn), `priority` (1 turn, preferred), `restricted` (2 turns, no waiting in flight), `blocked` (forbidden);
- simultaneous movement of all drones.

The program parses a map file, computes a conflict-free schedule, prints it turn by turn in the format required by the subject, and can animate it with `pygame` (`--visual`).

Constraints of the subject: no graph library, fully typed (`flake8` + `mypy`), fully object-oriented.

## Instructions

**Requirements:** Python 3.10+.

| Command | What it does |
|---|---|
| `make install` | Creates `venv/` and installs `pygame`, `flake8`, `mypy` |
| `make run` | Builds the `fly-in` launcher and runs `maps/01_linear_path.txt` with `--visual` |
| `make debug` | Runs `main.py` under `pdb` |
| `make lint` | `flake8 .` + `mypy` with the flags required by the subject |
| `make lint-strict` | `flake8 .` + `mypy --strict` |
| `make test` | Runs `run_tests.sh` on every map, comparing with the subject's targets |
| `make clean` / `fclean` | Removes caches / caches + `venv/` + launcher |

```bash
./fly-in maps/01_linear_path.txt            # text trace only
./fly-in maps/01_linear_path.txt --visual   # trace + pygame window
venv/bin/pip install pytest && venv/bin/python -m pytest -v   # unit tests
```

### Map format

```text
nb_drones: 5                                  # must be the first meaningful line
start_hub: hub 0 0 [color=green]              # exactly one
end_hub: goal 10 10 [color=yellow]            # exactly one
hub: roof1 3 4 [zone=restricted color=red]    # zone=normal|blocked|restricted|priority
hub: corridorA 4 3 [zone=priority max_drones=2]
connection: hub-roof1                         # zone names contain no dash and no space
connection: corridorA-tunnelB [max_link_capacity=2]
```

Any error (unknown zone, duplicate connection, bad metadata, unreachable end, ...) stops the program with a message such as `Parsing error: [Line 4] Invalid zone type: 'foo' (expected: normal, blocked, restricted, priority).`

### Example

Input — the example of the subject (chapter VI):

```text
nb_drones: 5

start_hub: hub 0 0 [color=green]
end_hub: goal 10 10 [color=yellow]
hub: roof1 3 4 [zone=restricted color=red]
hub: roof2 6 2 [zone=normal color=blue]
hub: corridorA 4 3 [zone=priority color=green max_drones=2]
hub: tunnelB 7 4 [zone=normal color=red]
hub: obstacleX 5 5 [zone=blocked color=gray]
connection: hub-roof1
connection: hub-corridorA
connection: roof1-roof2
connection: roof2-goal
connection: corridorA-tunnelB [max_link_capacity=2]
connection: tunnelB-goal
```

Output — 6 turns, one line per turn (`D3-hub-roof1` is D3 *in flight* on the connection towards the restricted zone `roof1`):

```text
D1-corridorA D3-hub-roof1
D1-tunnelB D2-corridorA D3-roof1
D1-goal D2-tunnelB D3-roof2 D4-corridorA
D2-goal D3-goal D4-tunnelB D5-corridorA
D4-goal D5-tunnelB
D5-goal
```

## Project structure

```text
.
├── main.py            Simulation      entry point, output of the trace
├── parser.py          Parser          reads and validates the map
├── router.py          SpaceTimeRouter the pathfinding / scheduling engine
├── models.py          Zone, Connection, ZoneType
├── window_config.py   WindowConfig    window size and map -> screen coordinates
├── visualizer.py      Visualizer      pygame animation
├── design/design_pattern.py  DesignPattern   colors, drawing helpers, drone icon
├── test_fly_in.py     pytest suite
├── run_tests.sh, Makefile, README.md
└── maps/, assets/     maps and optional images (background.jpg, drone.png)
```

```text
Simulation (main.py)
 |-- uses --> Parser ------------> Zone, Connection, ZoneType (models.py)
 |              '----------------> DesignPattern (color validation)
 |-- uses --> SpaceTimeRouter ---> Zone, Connection
 '-- uses --> Visualizer --------> WindowConfig (window size, coordinates)
                '----------------> DesignPattern (drawing helpers)
```

## Algorithm

### Choices

| Problem | Choice | Why |
|---|---|---|
| Drones must not collide, and a zone can be full *now* but free *later* | Search over **(zone, turn)** states — a space-time graph | Waiting becomes a normal move; capacity is checked per turn |
| Turn costs are 1 or 2, priority zones must break ties | **Dijkstra** with heap key `(turn, priority_score, counter)` | Turns are compared first (primary score of the subject), priority zones only decide between equally fast paths |
| Many drones share the map | **Prioritized planning**: route drone 1, reserve its path, route drone 2 around it, ... | Simple, deadlock-free (the schedule is fixed in time), each drone's path is optimal given the traffic before it |
| Restricted zones | Cost 2, reserved on the connection for 2 turns, no waiting on it | Exactly the rule of chapter VII.3 |

### Pipeline

```text
 map file
    |
    v
+-----------+      +------------------+      +----------------------------+
|  Parser   | ---> | SpaceTimeRouter  | ---> | Simulation                 |
|  validate |      | one path / drone |      | prints one line per turn   |
+-----------+      +------------------+      +----------------------------+
                           |
                           v
                   +------------------+
                   |   Visualizer     |   only with --visual
                   |   pygame window  |
                   +------------------+
```

### Routing all drones — `compute_all_routes`

```text
for drone i = 1 .. N
    |
    v
_find_path_for_drone()    best path given the reservations made so far
    |
    +-- no path found --> ValueError --> "Routing error", exit code 1
    |
    v
_reserve_path()           store (zone, turn) and (link, turn) usage
    |
    '--> next drone: it sees the reservations of all previous drones
```

Reservations are two dictionaries: `occupied_zones[(zone, turn)] = drones present` and `occupied_links[((a, b), turn)] = drones crossing`. Drone `i+1` sees the traffic of drones `1..i` as already fixed.

### One drone — `_find_path_for_drone`

```text
push (turn=0, score=0, start)
        |
        v
  .-> queue empty? --- yes --> return None
  |     | no
  |     v
  |   pop the smallest (turn, score, counter)
  |     |
  |     v
  |   zone == end? --- yes --> return the path
  |     | no
  |     v
  |   turn > horizon, or (zone, turn) already visited? --- yes --.
  |     | no                                                     |
  |     v                                                        |
  |   mark (zone, turn) as visited                               |
  |     |                                                        |
  |     +--> WAIT: push (turn+1, same zone)                      |
  |     |          only if the zone has room at turn+1           |
  |     |          (start and end zones: always allowed)         |
  |     |                                                        |
  |     '--> MOVE: for each neighbour that is not blocked:       |
  |              arrival = turn+1  (turn+2 if restricted)        |
  |              room in the neighbour at arrival                |
  |              AND room on the link?                           |
  |              (link checked at turn and turn+1 if restricted) |
  |                 yes --> push (arrival, score + priority      |
  |                         bonus, neighbour); a restricted move |
  |                         also adds a connection step          |
  |                 no  --> this move is dropped                 |
  |                                                              |
  '-------------------------- next iteration <-------------------'
```

The horizon is `10 * zones + 50 + 2 * drones` turns; if a drone cannot arrive within it, the program stops with `Routing error`.

### Simulation 1 — linear map, 2 drones (`start - waypoint1 - waypoint2 - goal`, all capacities 1)

**Drone 1** (empty map): pops `(0,start)`, moves to `waypoint1@1`, `waypoint2@2`, `goal@3`. It is reserved:

```text
turn        0        1          2          3
start       d1       .          .          .
waypoint1   .        d1         .          .
waypoint2   .        .          d1         .
goal        .        .          .          d1
```

**Drone 2** searches the same graph, but `(waypoint1, 1)` is now full:

| # | pop `(turn, zone)` | expansions |
|---|---|---|
| 1 | `(0, start)` | wait → push `(1, start)`; move to `waypoint1@1` ✗ **full (d1)** |
| 2 | `(1, start)` | wait → push `(2, start)`; move to `waypoint1@2` ✓ free, push |
| 3 | `(2, start)` | wait → push `(3, start)`; move to `waypoint1@3` ✓ push |
| 4 | `(2, waypoint1)` | move to `waypoint2@3` ✓ push; wait, or step back to `start@3` also pushed |
| … | states of turn 3 and 4 | `waypoint2@3` → `goal@4` |
| 17 | `(4, goal)` | **end reached → return** `start@0, start@1, waypoint1@2, waypoint2@3, goal@4` |

Final schedule (`d2` waits one turn *strategically* at the start, output omits waiting drones):

```text
turn        0      1      2      3      4
start       d1 d2  d2     .      .      .
waypoint1   .      d1     d2     .      .
waypoint2   .      .      d1     d2     .
goal        .      .      .      d1     d2

D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal                        -> 4 turns (subject's target: <= 6)
```

### Simulation 2 — the subject's example, 5 drones (restricted, priority and capacities)

Paths found, one drone after the other (`*` = in flight on a connection towards a restricted zone):

```text
d1: hub@0 corridorA@1 tunnelB@2 goal@3
d2: hub@0 hub@1 corridorA@2 tunnelB@3 goal@4
d3: hub@0 hub-roof1@1* roof1@2 roof2@3 goal@4
d4: hub@0 hub@1 hub@2 corridorA@3 tunnelB@4 goal@5
d5: hub@0 hub@1 hub@2 hub@3 corridorA@4 tunnelB@5 goal@6
```

```text
turn   D1          D2          D3           D4          D5
0      hub         hub         hub          hub         hub
1      corridorA   hub         hub-roof1*   hub         hub
2      tunnelB     corridorA   roof1        hub         hub
3      goal        tunnelB     roof2        corridorA   hub
4                  goal        goal         tunnelB     corridorA
5                                           goal        tunnelB
6                                                       goal
```

Why the decisions are what they are:

- **d1** reaches `goal` at turn 3 through `corridorA` (priority) and `tunnelB`; the route through `roof1` (restricted, 2 turns) would arrive at turn 4.
- **d2** has a *tie*: `corridorA → tunnelB → goal` (arrival 4) and `roof1 → roof2 → goal` (arrival 4). The heap key `(turn, priority_score, …)` breaks it: the `priority` zone gives score −1, so `corridorA` wins. Without this second key the tie would be arbitrary.
- **d3**: the entrance of the corridor is busy (the link `hub–corridorA`, capacity 1, is taken at turns 0 and 1), so d3 could only enter it at turn 3 and would arrive at turn 5. The restricted route arrives at turn 4, so it is chosen — this is how the load is **distributed across several paths**. Its link `hub–roof1` is reserved for turns 0 and 1, and it cannot wait on it.
- **d4, d5** wait at `hub` (unlimited capacity) until the corridor is free: one drone enters per turn, which is the throughput of the bottlenecks (`hub–corridorA` capacity 1, `tunnelB` with `max_drones=1`).

## Answers to the questions of the subject

### How efficient is the algorithm? Can it work with a large number of drones?

Each drone's path is **optimal** for the traffic already reserved (fewest turns, then most priority zones): Dijkstra on a time-expanded graph with non-negative costs. The fleet schedule is built greedily (see *Accuracy*). Measured on synthetic maps (Python 3, one machine, `SpaceTimeRouter.compute_all_routes` only):

| Map | Zones | Drones | Turns | Time | Peak memory |
|---|---|---|---|---|---|
| Linear corridor | 10 | 100 | 108 | 0.2 s | 0.7 MB |
| Linear corridor | 10 | 500 | 508 | 2.6 s | 11.6 MB |
| Linear corridor | 10 | 1000 | 1008 | 9.6 s | 48.4 MB |
| 6×6 grid | 36 | 200 | 109 | 1.8 s | 1.4 MB |
| 10×10 grid | 100 | 200 | 117 | 10.2 s | 2.4 MB |

So a thousand drones are handled, but the cost grows quickly with the fleet (see below). No number of drones is hard-coded; the only limit is the turn horizon described above.

### What is the complexity? Why?

Notation: `Z` zones, `E` connections, `N` drones, `M` number of turns of the schedule, `L` length of a path (`L ≤ M`).

- **Parser:** `O(lines)` plus one DFS `O(Z + E)` to check that the end is reachable before routing.
- **One drone:** the search only visits states `(zone, turn)` with `turn ≤` its arrival turn, i.e. at most `Z · M` states. Each state creates 1 wait + `deg(zone)` moves, so at most `M · (Z + 2E)` heap pushes, each `O(log)`. Each push also **copies the path** (`path + [...]`), which costs `O(L)`. This gives `O(M · (Z + E) · (log + M))` per drone.
- **Whole fleet:** `N` searches, so `O(N · M · (Z + E) · (log + M))`. This is an upper bound; on a corridor (`M ≈ N`) the measured time grows roughly with `N²` (table above).
- **Why this cost:** the factor `M` exists because waiting is allowed, so a zone becomes `M` states. The `log` comes from the heap (needed because moves cost 1 or 2 and priority zones break ties). The extra `M` comes from copying paths, which we kept for readability; storing a parent pointer per state instead would remove it (`O(N · M · (Z + E) · log)`).

### Are paths recalculated or cached?

Never recalculated: every drone is routed **once**. The result (`routes`) is reused by the trace printer and by the visualizer. Between drones nothing can be cached: each path depends on the reservations created by the previous ones, and those reservations (`occupied_zones`, `occupied_links`) are the shared state. The visualizer only interpolates stored routes; it never routes again.

### How does it impact memory?

- Reservations and stored routes: `O(N · L)` entries.
- During one search: `visited` is `O(Z · M)` and freed after each drone; the heap holds path copies (`O(L)` each), which is the dominant peak (48 MB for 1000 drones on a corridor).

### How does the visual representation help?

See *Visual representation* below.

### Accuracy — how close to the best schedule?

- **Per drone:** exact (see above).
- **Whole fleet:** not guaranteed optimal. Prioritized planning is a heuristic: drone 1 always takes its best path, even if a slightly slower path for drone 1 would let the others finish earlier, and the result depends on the drone order.
- **Check against a lower bound.** If `k` drones can leave the start per turn and the shortest path has `d` moves, no schedule can beat `ceil(N / k) + d − 1` turns. On the synthetic maps above our result **equals** this bound every time:

| Map | `k` | `d` | Lower bound | Ours |
|---|---|---|---|---|
| Linear corridor, 10 drones | 1 | 9 | 18 | 18 |
| Linear corridor, 1000 drones | 1 | 9 | 1008 | 1008 |
| 6×6 grid, 50 drones | 2 | 10 | 34 | 34 |
| 6×6 grid, 200 drones | 2 | 10 | 109 | 109 |
| 10×10 grid, 200 drones | 2 | 18 | 117 | 117 |

- **Possible improvements:** try several drone orders and keep the best schedule; or a global search over the time-expanded graph (max-flow style).

### Performance benchmarks

Run `make test` to compare the maps of the subject with their targets (`run_tests.sh` prints ✅ when the result is within target).

| Map | Drones | Target | Ours |
|---|---|---|---|
| Linear path | 2 | ≤ 6 | TBD |
| Simple fork | 4 | ≤ 8 | TBD |
| Basic capacity | 4 | ≤ 6 | TBD |
| Dead end trap | 5 | ≤ 12 | TBD |
| Circular loop | 6 | ≤ 15 | TBD |
| Priority puzzle | 5 | ≤ 12 | TBD |
| Maze nightmare | 8 | ≤ 30 | TBD |
| Capacity hell | 12 | ≤ 35 | TBD |
| Ultimate challenge | 15 | ≤ 45 | TBD |
| Impossible dream (optional) | 25 | record 45 | TBD |

**Optimizations implemented:** turn count compared first and priority only as a tie-break; early exit as soon as the end is popped; pruning of already visited `(zone, turn)` states; `O(1)` dictionary reservations; adjacency list built once; unlimited waiting at start/end; reachability check in the parser before routing; a single routing pass reused by every output.

**Challenger map:** solving it is optional. As the fleet planning is greedy, beating the reference record is not guaranteed; the improvements listed in *Accuracy* are the next steps.

## Visual representation

`python main.py <map> --visual` opens a `pygame` window; the terminal trace is still printed.

- Every zone is a circle colored by its `color` metadata (`rainbow` is drawn as a gradient), labeled `name [drones/max]`.
- Every connection is a line labeled `used/cap:N`; a link being crossed turns thick and yellow, so bottlenecks are visible.
- All drones move **simultaneously** and smoothly between zones (interpolation), showing at a glance who waits and where traffic queues up.
- A HUD shows `Turn: x / total` and the state (running or paused).
- Drones sharing a zone are spread in a small circle so their identifiers stay readable.

| Key | Action |
|---|---|
| `SPACE` | Pause / resume |
| `RIGHT ARROW` or `P` | Force the next turn |

Missing `assets/background.jpg` or `assets/drone.png` never crashes the program (plain background and a vector drone are used instead).

## Testing

- `python -m pytest -v` (`test_fly_in.py`): parser (valid and 44 invalid maps), routing scenarios with their optimal turn count, restricted/blocked/priority rules, 150 drones, clean error exits, the real command line, and every map of `maps/`. Each trace is re-checked by an **independent validator** (zone and link capacities, 2-turn restricted moves, everyone delivered).
- `make lint` / `make lint-strict`: `flake8` and `mypy` (both mandatory, both clean).

## Resources

- Python documentation: [`heapq`](https://docs.python.org/3/library/heapq.html), [`typing`](https://docs.python.org/3/library/typing.html), [`enum`](https://docs.python.org/3/library/enum.html), [`re`](https://docs.python.org/3/library/re.html)
- [pygame documentation](https://www.pygame.org/docs/), [mypy](https://mypy.readthedocs.io/en/stable/), [flake8](https://flake8.pycqa.org/en/latest/), [pytest](https://docs.pytest.org/)
- Cormen, Leiserson, Rivest, Stein — *Introduction to Algorithms* (single-source shortest paths); [Dijkstra's algorithm](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm)
- Silver, D. — *Cooperative Pathfinding* (space-time A*, prioritized planning); search terms: "Multi-Agent Path Finding", "Prioritized Planning"

### How AI was used

An Anthropic Claude model was used for the following tasks:

- **Makefile:** reviewing the rules so that they use the virtual environment and match the `lint` / `lint-strict` commands of the subject.
- **Understanding:** explaining the space-time Dijkstra in `router.py`, its complexity, and the regular expressions of `parser.py`.
- **Parser:** hardening the metadata validation (unknown/duplicate keys, non-positive capacities, nested brackets, invalid colors).
- **Router:** finding a bug where a longer path through priority zones could beat a shorter one; the heap key now compares turns first.
- **Object-oriented refactoring:** turning loose functions of `main.py`, `visualizer.py` and `design_pattern.py` into classes.
- **Review against the subject (v1.6):** translating every message and docstring to English; finding that the in-flight connection label must be `<zone1>-<zone2>`, that the pygame banner polluted the trace, and that `run_tests.sh` used wrong targets and opened a blocking window.
- **Tests and lint:** writing the pytest suite and its independent trace validator, and fixing a flake8 `E402` warning in `design_pattern.py`.
- **Documentation:** drafting this README and its diagrams, and measuring the synthetic benchmarks above.

All AI-assisted code was read, run against the tests, `flake8` and `mypy`, and is understood and explainable by the author.
