*This project has been created as part of the 42 curriculum by nrajaoar.*

# Fly-in — Multi-Drone Space-Time Routing Simulator

## Table of Contents

- [Description](#description)
- [Features](#features)
- [Project Structure](#project-structure)
- [Instructions](#instructions)
- [Map File Format](#map-file-format-quick-reminder)
- [Algorithm](#algorithm)
  - [Overview](#overview)
  - [Why a Space-Time Graph?](#why-a-space-time-graph)
  - [How a Single Drone Finds Its Path](#how-a-single-drone-finds-its-path--step-by-step)
  - [Coordinating Multiple Drones — Prioritized Planning](#coordinating-multiple-drones--prioritized-planning)
  - [Worked Example](#worked-example)
  - [Complexity Analysis](#complexity-analysis)
  - [Why This Algorithm Is Efficient](#why-this-algorithm-is-efficient)
  - [Limitations](#limitations)
- [Key Functions Explained](#key-functions-explained)
- [Visual Representation](#visual-representation)
- [Resources](#resources)

---

## Description

Fly-in is a drone-fleet routing simulator. Given a map of interconnected **zones**
(a graph) and a fleet of `N` drones, the program computes, for every drone, the
fastest valid path from a single start zone to a single end zone — while
respecting per-zone drone capacity, per-connection traffic capacity, variable
zone movement costs, and truly simultaneous multi-drone movement.

The goal is not just "find a path" but "find a *schedule*": since every drone
shares the same map at the same time, the interesting part of the problem is
deciding who moves when, so that drones don't collide, overflow a zone's
capacity, or exceed a connection's traffic limit.

The simulation exposes two ways to inspect the result:
- A structured, turn-by-turn text trace printed to the terminal, in the exact
  format required by the subject (`D<ID>-<zone>` per moving drone, per turn).
- An optional real-time animated graphical visualization built with `pygame`
  (`--visual` flag), showing every drone moving simultaneously across the
  network, with pause/step playback controls.

The whole project is implemented from scratch, without any graph library
(forbidden by the subject), and is split into clear responsibilities:

| File | Responsibility |
|---|---|
| `parser.py` | Reads and validates the map file, builds `Zone`/`Connection` objects |
| `router.py` | The pathfinding engine — computes a conflict-free schedule for every drone |
| `models.py` | The data model: `Zone`, `Connection`, `ZoneType` |
| `main.py` | Entry point: argument handling, orchestration, text output |
| `window_config.py` | Computes an appropriate `pygame` window size and coordinate mapping |
| `visualizer.py` | The `pygame` animation loop |
| `design/design_pattern.py` | Colors, drawing helpers, and the drone icon |

## Features

- Custom line-based parser with clear, line-numbered error messages, and
  strict metadata validation (unknown keys, duplicate keys, malformed
  `key=value` pairs, nested brackets, non-positive capacities, and unknown
  color names are all rejected rather than silently ignored).
- Four zone types (`normal`, `blocked`, `restricted`, `priority`), each with its
  own movement rules.
- Per-zone drone capacity (`max_drones`) and per-connection traffic capacity
  (`max_link_capacity`).
- Sequential multi-drone routing that keeps every drone's path conflict-free
  with every drone planned before it.
- Turn-by-turn text output matching the subject's required format.
- Optional real-time `pygame` visualization with interpolated drone movement,
  active-link highlighting, and playback controls.
- Fully typed codebase (`mypy`-checked) and `flake8`-compliant.
- A `Makefile` automating install, run, debug, lint, test, and clean workflows.

## Project Structure

```text
.
├── Makefile
├── README.md
├── main.py                    # Entry point: parses args, drives the pipeline
├── parser.py                  # Map file parser (Parser class)
├── router.py                  # Space-time pathfinding engine (SpaceTimeRouter class)
├── models.py                  # Zone, Connection, ZoneType
├── window_config.py           # Dynamic pygame window sizing (WindowConfig class)
├── visualizer.py               # Pygame animation loop (run_visualizer)
├── design/
│   ├── __init__.py            # Marks design/ as an importable Python package
│   └── design_pattern.py      # Drawing helpers, colors, drone icon
└── maps/                      # Map files (.txt), one per test scenario
```

`design/__init__.py` is intentionally empty — its only role is to tell Python
that `design/` is a package, which is what makes
`from design.design_pattern import ...` (used in `visualizer.py`) work at all.

## Instructions

### Requirements

- Python 3.10 or later
- `pip` (used inside a virtual environment created by `make install`)

### Setup

```bash
make install
```

Creates a local virtual environment (`venv/`) and installs `pygame`, `flake8`,
and `mypy` into it.

### Running the simulation

```bash
make run
```

Builds the `fly-in` launcher script and runs it against the default demo map
(`maps/01_linear_path.txt`) with the graphical visualizer enabled.

To run a specific map, or without the visualizer:

```bash
./fly-in maps/01_linear_path.txt            # text output only
./fly-in maps/01_linear_path.txt --visual   # text output + pygame window
```

While the `pygame` window is open:

| Key | Action |
|---|---|
| `Space` | Pause / resume the animation |
| `→` or `P` | Step forward one simulation turn manually |

### Debugging

```bash
make debug
```

Runs `main.py` under Python's built-in debugger (`pdb`), paused at the very
first line. Useful commands once inside `pdb`:

| Command | Effect |
|---|---|
| `n` | Execute the next line (step over) |
| `s` | Step into the function being called |
| `c` | Continue until the next breakpoint (or the end) |
| `p <expr>` | Print the value of a variable or expression |
| `l` | List the source code around the current line |
| `b file.py:42` | Set a breakpoint at line 42 of `file.py` |
| `q` | Quit the debugger |

For a more targeted session, insert `import pdb; pdb.set_trace()` directly
inside `router.py` — for example right before the `while queue:` loop — to
pause exactly at the point of interest and inspect the search's live state
(`p queue`, `p occupied_zones`, ...).

### Linting

```bash
make lint          # flake8 + mypy with the flags required by the subject
make lint-strict    # flake8 + mypy --strict (recommended, optional)
```

### Cleaning

```bash
make clean   # removes __pycache__, .mypy_cache, temp files
make fclean  # clean + removes the virtual environment and the fly-in launcher
make re      # fclean + all (full rebuild)
```

## Map File Format (quick reminder)

```text
nb_drones: <positive integer>

start_hub: <name> <x> <y> [metadata]
end_hub: <name> <x> <y> [metadata]
hub: <name> <x> <y> [metadata]

connection: <name1>-<name2> [metadata]
```

- `metadata` is optional, e.g. `[zone=restricted color=red]`, `[max_drones=2]`,
  `[max_link_capacity=2]`.
- Zone types: `normal` (1 turn, default), `priority` (1 turn, should be
  preferred by the router), `restricted` (2 turns), `blocked` (impassable).
- Lines starting with `#` are comments and are ignored.

See the subject PDF (Chapter VI) for the full specification.

---

## Algorithm

### Overview

The routing engine (`SpaceTimeRouter` in `router.py`) is a **Dijkstra's
algorithm search over a space-time expanded graph**, applied to each drone
**one after another** — a technique commonly called **Prioritized Planning**
(or Sequential / Cooperative Pathfinding) in multi-agent pathfinding
literature.

In plain terms:
- Dijkstra's algorithm finds the cheapest way from A to B in a graph by always
  exploring the cheapest known option first.
- *"Space-time expanded"* means the search treats *"zone X at turn T"* as a
  state completely distinct from *"zone X at turn T+1."* This is what lets the
  algorithm know that a zone can be occupied right now but free two turns
  later.
- *"Prioritized Planning"* means the drones are not all planned together as one
  giant problem (which would be far more expensive). Instead, drone 1 gets the
  best possible path for itself; that path is then reserved; drone 2 is
  planned around that reservation; and so on.

### Why a Space-Time Graph?

A plain graph search only knows *"is zone X reachable from zone Y?"* — it has
no notion of *when*. But this project's rules are fundamentally about timing:
a zone might be free right now but full in two turns, because another drone is
already scheduled to be there then. An ordinary Dijkstra over
`(zones, connections)` cannot express that at all.

The fix used here: every state explored by the search is a pair
**`(zone name, turn number)`**, not just a zone name:

```python
visited: Set[Tuple[str, int]] = set()
...
if (curr_name, tour) in visited:
    continue
```

and every reservation made for a completed drone is keyed the same way:

```python
self.occupied_zones: Dict[Tuple[str, int], int] = {}
self.occupied_links: Dict[Tuple[Tuple[str, str], int], int] = {}
```

This is exactly what lets `"mid" at turn 1` be full while `"mid" at turn 2` is
free, and lets the router treat "stay" and "move" as two entirely separate
options, each with its own cost.

### How a Single Drone Finds Its Path — Step by Step

`_find_path_for_drone` keeps a priority queue (min-heap) of *"partial
journeys."* Each entry is a tuple `(total_cost, arrival_turn, current_zone,
path_so_far)`. The search repeats the following loop:

1. **Pop the cheapest partial journey** from the queue. Because it's a
   min-heap, this is always the least-costly option discovered so far — this
   is Dijkstra's core guarantee: the first time the destination is popped, the
   path that got there is provably the cheapest possible.
2. **If the current zone is the destination**, return the path immediately —
   done.
3. **If this exact `(zone, turn)` state was already explored**, skip it — no
   need to explore the same state twice.
4. **Otherwise, generate every valid next state**:
   - **Wait one turn** in the current zone (always allowed in the start and
     end zones; elsewhere, only if the zone still has capacity one turn from
     now).
   - **Move to each connected neighbor**, provided:
     - the neighbor is not `blocked`,
     - the neighbor zone has room at the turn the drone would arrive
       (`max_drones`),
     - the connection itself has room at the turn it would be crossed
       (`max_link_capacity`).
   - The cost of moving depends on the neighbor's type: **2 turns for
     `restricted` zones, 1 turn otherwise** (`normal` and `priority`).
5. Push every valid next state back onto the queue, and repeat from step 1.

Because the queue always pops the cheapest option first, and every rule
(capacity, blocked zones, restricted-zone cost) is checked *before* a state is
even added to the queue, the search never wastes time exploring — and then
discarding — an invalid state: invalid moves are simply never generated in
the first place.

> **A small detail worth noticing.** In this implementation, `cost` and `tour`
> always increase by exactly the same amount at every step (both grow by `1`
> for a normal move or a wait, and by `2` for a move into a `restricted`
> zone), so the two values stay numerically identical throughout the search.
> That is expected here, since the whole point is to minimize the number of
> turns — `cost` is, in effect, just a turn counter used as Dijkstra's
> priority. The two fields are kept separate mainly for clarity (and because a
> future extension — a distinct weighted-scoring mode, for instance — could
> make them diverge).

### Coordinating Multiple Drones — Prioritized Planning

`compute_all_routes` drives the whole fleet:

```python
for i in range(1, nb_drones + 1):
    path = self._find_path_for_drone(start, end)
    ...
    all_paths[drone_id] = path
    self._reserve_path(path)
```

Each drone is planned **completely independently**, but against a map that
"remembers" every previous drone's reservations. Once a drone's path is found,
`_reserve_path` writes every `(zone, turn)` and `(connection, turn)` it uses
into `occupied_zones` / `occupied_links`. The next drone's search then sees a
slightly more crowded map, and Dijkstra naturally routes it around the
reserved zones and connections — waiting if needed, or taking a different path
if one is available and cheaper than waiting.

### Worked Example

Consider this tiny three-zone map with **2 drones**:

```text
nb_drones: 2

start_hub: base 0 0
end_hub: goal 2 0
hub: mid 1 0 [max_drones=1]

connection: base-mid
connection: mid-goal
```

```text
   (start)                (capacity: 1)                 (end)
  ┌────────┐             ┌───────────┐               ┌────────┐
  │  base  │─────────────│    mid    │───────────────│  goal  │
  └────────┘             └───────────┘               └────────┘
```

`mid` only allows **one drone at a time**. Here is what the router computes,
turn by turn:

| Turn | Drone 1 (D1) | Drone 2 (D2) | Why |
|---|---|---|---|
| 0 | at `base` | at `base` | both start together — the start zone has no capacity limit |
| 1 | → `mid` | waits at `base` | D1 reaches `mid` first; D2's own move into `mid` at turn 1 would exceed `mid`'s capacity of 1, so the router makes D2 wait instead |
| 2 | → `goal` (delivered) | → `mid` | `mid` is free again once D1 has left it |
| 3 | — | → `goal` (delivered) | D2 finishes one turn later than D1, purely because of the wait |

Resulting simulation output, exactly as `main.py` prints it:

```text
D1-mid D2-base
D1-goal D2-mid
D2-goal
```

> **Implementation note.** Look closely at the first line: `D2-base` appears
> even though D2 did not actually move — it *waited* at `base`. Internally,
> every turn spent waiting is stored in the path as `(same_zone, turn + 1)`,
> exactly like a real move, and `main.py`'s output loop does not currently
> distinguish between the two. The subject specifies that "drones that do not
> move in a given turn are omitted from that line" — as written, a pure wait
> is not filtered out before printing. Worth checking against the exact
> evaluation maps; an easy fix, if needed, is to compare a drone's zone at
> `turn` and `turn - 1` before emitting an action for it.

### Complexity Analysis

Let:
- **V** = number of zones on the map
- **E** = number of connections on the map
- **T** = number of turns explored before a path is found (the time horizon)
- **N** = number of drones

**Why `log` shows up at all.** The priority queue (`heapq`) is a *binary
heap*: internally, a binary tree stored in an array and kept arranged so the
smallest element is always on top. Every push or pop has to move an element up
or down that tree to restore the ordering — and a binary tree holding `n`
elements only has `log₂(n)` levels. So each push/pop costs `O(log n)`, not
`O(n)`. The gain is dramatic:

| Elements queued (n) | Cost of scanning for the minimum (O(n)) | Cost of a heap push/pop (O(log₂ n)) |
|---|---|---|
| 10 | 10 | ≈ 3.3 |
| 1,000 | 1,000 | ≈ 10 |
| 1,000,000 | 1,000,000 | ≈ 20 |

Even with a million entries queued, a heap operation only costs about 20
comparisons — this is why Dijkstra with a heap scales so much better than
repeatedly scanning a plain list for the smallest element.

**Per-drone cost.** Because the router searches over `(zone, turn)` pairs
instead of plain zones, the *effective* graph it explores is `T` times bigger
than the raw map:
- number of states ≈ `V · T` (every zone, duplicated across every turn)
- number of transitions ≈ `E · T` (every connection, duplicated across every
  turn)

Plugging these into the standard Dijkstra complexity formula
`O((states + transitions) · log(states))` gives, for a single drone:

```text
O((V·T + E·T) · log(V·T))
```

**Whole-fleet cost.** `compute_all_routes` repeats this search once per drone,
sequentially:

```text
O(N · (V·T + E·T) · log(V·T))
```

### Why This Algorithm Is Efficient

- **No graph-library overhead or dependency.** Everything is built on Python's
  `heapq`, a pure generic heap data structure with zero graph-specific logic —
  satisfying the subject's constraint (Chapter V) without sacrificing
  performance.
- **Constraints are enforced *during* generation, not after.** Capacity
  checks, blocked zones, and restricted-zone costs are all evaluated *before*
  a state is ever pushed onto the queue — the search never wastes time
  exploring, and then discarding, an invalid path.
- **Variable movement costs need no special-casing.** A `restricted` zone
  simply costs `2` instead of `1` in the exact same cost formula used for
  every other zone type — no separate code path is required.
- **Avoids the combinatorial explosion of true multi-agent search.** Planning
  all `N` drones *jointly* (searching the combined state of every drone at
  once) is a dramatically harder problem in general. By solving one drone at a
  time and reserving its path before moving to the next, the problem stays a
  sequence of `N` ordinary single-agent shortest-path searches — each one
  comfortably solvable with classic Dijkstra.

### Limitations

- **Not globally optimal across the fleet.** Drone 1 always gets the cheapest
  path *for itself*, with no regard for how that choice affects drone 2,
  drone 3, and so on. A drone willing to take a one-turn detour could
  sometimes unblock a much shorter path for a later drone — but this algorithm
  never considers that trade-off. A fully optimal solution would need a joint
  multi-agent search (e.g. Conflict-Based Search), at a much higher
  implementation and runtime cost.
- **Later drones inherit an increasingly congested map.** On maps with many
  drones funneling through a narrow bottleneck (the "Capacity hell" or
  "Ultimate challenge" benchmark categories from the subject), drones planned
  later in the sequence are more likely to face long waits, since earlier
  drones have already claimed the fastest slots.
- **`priority` zones are not actually preferred.** The subject states that
  `priority` zones "should be prioritized in pathfinding," but in the current
  cost model `priority` and `normal` zones share the exact same `travel_cost`
  of `1`. Dijkstra therefore treats them identically — it has no reason to
  route a drone through a `priority` zone over a `normal` one of equal cost. A
  small negative bias, or a tie-breaking preference favoring `priority` zones,
  would be needed to fully honor this requirement.
- **The wait/move ambiguity in the printed output**, described in the
  [Worked Example](#worked-example) above.

---

## Key Functions Explained

### `Parser.parse_file` — Reading the Map, Line by Line

Reads the file with a context manager (`with open(...) as f`) so the file
handle is always closed, even if parsing fails partway through. Every line is
wrapped in its own `try/except`, and any error is re-raised with the exact
line number attached — satisfying the subject's requirement (VII.4) that
*"any other parsing error must stop the program and return a clear error
message indicating the line and cause."*

Zone-declaration lines (`start_hub:`, `end_hub:`, `hub:`) are recognized and
decomposed with a single regular expression, explained in full below.

### `Parser.parse_metadata` — Reading `[key=value ...]` Blocks

Turns a metadata string such as `zone=restricted color=red` into a dictionary
`{"zone": "restricted", "color": "red"}` — matching the subject's rule that
"tags inside brackets can appear in any order."

Unlike a permissive regex-based extractor, this parser is **strict by
design**: rather than silently ignoring anything that doesn't look like a
valid tag, every token inside the brackets is explicitly validated, and any
anomaly stops parsing with a clear, line-numbered error. Specifically, it
rejects:

- **Unknown keys** — only `zone`, `color`, `max_drones`, and
  `max_link_capacity` are recognized. A typo such as `xcolor=green` is
  rejected rather than silently ignored, since the subject requires "any
  other parsing error" to stop the program with a clear message (VII.4).
- **Duplicate keys within the same block** — `[zone=restricted
  zone=blocked]` or `[color=blue color=white]` raises an error instead of
  silently keeping the last value, since a repeated key in the same bracket
  is inherently ambiguous.
- **Malformed `key=value` pairs** — a token like `=value` or `key=` (empty
  key or value) is rejected.
- **Nested or unbalanced brackets** — a block such as `[[color=red]]` is
  rejected rather than being silently unwrapped.
- **Non-positive or non-integer capacity values** — `max_drones` and
  `max_link_capacity` must be strictly positive integers, per the subject's
  explicit requirement ("Capacity values ... must be positive integers,"
  VII.4). A value like `max_drones=0` or `max_link_capacity=salut` is
  rejected with a dedicated error message.
- **Unknown color names** — every `color` value (except the special
  `rainbow` value used for the Challenger map's goal zone, rendered as a
  multicolor gradient) is validated against `pygame.Color`'s recognized color
  names at parse time, so a typo like `color=rainbou` fails immediately
  instead of only surfacing later when `--visual` is used.

This trades a small amount of leniency for predictability: a malformed map
fails fast, at the exact line responsible, with a message describing exactly
what was wrong — rather than silently accepting a typo and producing a
subtly incorrect simulation.

### Regex Crash Course (for the Patterns Used in `parser.py`)

| Token | Meaning |
|---|---|
| `\d` | one digit (`0`–`9`) |
| `\w` | one "word" character (letter, digit, or `_`) |
| `\s` | one whitespace character (space, tab, newline) |
| `+` | one or more of the previous token |
| `*` | zero or more of the previous token |
| `?` | zero or one of the previous token (makes it optional) |
| `(...)` | a *capturing* group — its match can be retrieved afterward |
| `(?:...)` | a *non-capturing* group — groups tokens together without keeping the match |
| `[^...]` | any character **except** the ones listed |
| `^` / `$` | start / end of the string |
| `\b` | a word boundary (the edge between a word character and a non-word one) |
| `\|` | "or" |

**Metadata tokenization — no longer regex-based**

An earlier version of this parser extracted `key=value` pairs using a single
regular expression with `re.findall`:

```python
r"(\w+=\w+|\bzone\s+\w+|\bcolor\s+\w+)"
```

That approach was replaced. `findall` silently *skips* any substring that
doesn't match one of its alternatives, which meant a typo or an unrecognized
tag (e.g. `xcolor=green`, or a stray token like `xx`) would simply disappear
from the metadata without ever raising an error — exactly the kind of "clear
error message indicating the line and cause" the subject requires (VII.4)
was missing. It also could not detect duplicate keys, malformed pairs, or
nested brackets, since it only ever looked for fragments that *did* match,
never flagged what didn't.

`parse_metadata` now works by splitting the bracket's contents on whitespace
and validating each token explicitly — checking for a recognized key, a
non-empty value, no duplicate keys, and no leftover brackets — rather than
relying on a regex to opportunistically find valid-looking fragments
anywhere in the string. The two remaining regexes in the file — extracting a
zone-declaration line's fields, and locating a connection's `[...]` block —
are unchanged and still described below.

**Pattern 1 — parsing a zone-declaration line**

```python
r"^(start_hub|end_hub|hub):\s*([^\s\[\-]+)\s+(-?\d+)\s+(-?\d+)(?:\s+\[(.*)\])?$"
```

Applied to `start_hub: hub 0 0 [color=green]`:

| Part of the pattern | Meaning | Captured here |
|---|---|---|
| `^` | start of the line | — |
| `(start_hub\|end_hub\|hub):` | one of the three prefixes, then a literal `:` | `start_hub:` |
| `\s*` | optional whitespace | ` ` |
| `([^\s\[\-]+)` — group 2 | one or more characters that are **not** whitespace, `[`, or `-` | `hub` (the zone name) |
| `\s+` | required whitespace | ` ` |
| `(-?\d+)` — group 3 | an optional `-` then digits (a signed integer) | `0` |
| `\s+` | whitespace | ` ` |
| `(-?\d+)` — group 4 | another signed integer | `0` |
| `(?:\s+\[(.*)\])?` | an **entirely optional** block: whitespace, `[`, anything (group 5), `]` | `[color=green]` → group 5 = `color=green` |
| `$` | end of the line | — |

Note the choice of `[^\s\[\-]+` (instead of the more common `\w+`) for the
zone name: the subject explicitly allows "any valid characters but dashes and
spaces" in a name, and `\w+` would wrongly reject a perfectly legal character
such as `.` or `'`. `[^\s\[\-]+` matches that constraint exactly as written.

When the `[...]` block is absent, group 5 is simply `None` — handled in the
code with `meta_str if meta_str else ""`.

**Pattern 2 — extracting a connection's metadata block**

```python
re.search(r"\[(.*)\]", rest_part)
```

`re.search` looks for the pattern *anywhere* in the string (unlike
`re.match`, which only anchors at the start). `\[(.*)\]` grabs everything
between the first `[` and the last `]`. The same pattern is then reused with
`re.sub(r"\[.*\]", "", rest_part)` to strip that metadata block back out,
leaving only the plain `zone1-zone2` behind.

> **Regex gotcha — greedy vs. lazy.** `.*` is *greedy*: it grabs as much text
> as it possibly can. On an input like `[a] text [b]`, `\[(.*)\]` would
> actually capture `a] text [b` — from the *first* `[` all the way to the
> *last* `]`, not just `a`. This never causes a problem for well-formed
> single-bracket lines, but it is exactly why `[[color=red]]` (nested
> brackets) reaches `parse_metadata` still containing a leftover `[` and `]`
> instead of being cleanly unwrapped by the regex alone — which is precisely
> the case `parse_metadata`'s own bracket check is there to catch. The fix
> for genuinely wanting the *first* bracket pair only, if ever needed, is the
> *lazy* quantifier `.*?` (note the extra `?`), which stops at the first `]`
> it finds instead of the last.

### `SpaceTimeRouter.__init__` — Building the Adjacency List

Builds `self.adj`, a dictionary mapping every zone name to the list of
`(neighbor_zone, connection)` pairs reachable from it. Since connections are
bidirectional (subject, Chapter VI), each connection is registered on
**both** of its endpoints:

```python
for conn in connections:
    self.adj[conn.zone1.name].append((conn.zone2, conn))
    self.adj[conn.zone2.name].append((conn.zone1, conn))
```

### `SpaceTimeRouter.compute_all_routes` and `_find_path_for_drone`

Covered in detail in the [Algorithm](#algorithm) section above — the former
drives the fleet one drone at a time, the latter is the per-drone space-time
Dijkstra search.

### `SpaceTimeRouter._reserve_path` — Locking In a Found Path

Once a drone's path is found, this walks it turn by turn, incrementing
`occupied_zones[(zone, turn)]` for every step. Whenever two consecutive steps
land on *different* zones, it also increments
`occupied_links[(sorted_pair, turn)]` for the connection that was crossed.
Sorting the pair of zone names before using it as a dictionary key
(`sorted([zone_name, next_zone_name])`) guarantees that a connection is
recognized as "the same connection" no matter which direction it is crossed
in — `base → mid` and `mid → base` must count against the same shared
capacity, since connections are bidirectional.

### `WindowConfig` — Sizing the pygame Window

Computes an appropriate window size purely from the spread of zone
coordinates on the map, so a tiny 3-zone map doesn't open a cavernous empty
window and a large sprawling map isn't cramped — clamped between a sensible
minimum and the actual screen resolution. `to_screen_coords` then converts a
zone's map coordinates into pixel coordinates, flipping the Y axis (screen
coordinates grow downward; map coordinates conventionally grow upward) and
anchoring everything within the drawable margin.

### `run_visualizer` — The Animation Loop

For every rendered frame, and for each drone independently, the loop
determines the drone's "current" and "next" zone in its own path based on the
current simulation turn, then linearly interpolates its on-screen pixel
position between the two using a `progress` value that increases every frame
and resets once a turn boundary is crossed. This interpolation is what
produces smooth, continuous motion instead of drones instantly jumping from
one zone to the next once per turn.

---

## Visual Representation

The `pygame` visualizer turns the raw turn-by-turn text trace into a live,
readable animation, satisfying the subject's Visual Representation
requirement (VII.1) through a graphical interface.

What it shows, and why it helps:

- **All drones animate simultaneously**, matching the simulation's actual
  rules — this makes it immediately obvious, at a glance, whether drones are
  genuinely moving together or queuing up behind one another.
- **Zones are colored by type** (`normal` = blue, `blocked` = red,
  `restricted` = orange, `priority` = green by default, or a custom color
  from the map file), each labeled with its name and maximum capacity — so a
  capacity bottleneck is visible before it even happens in the simulation.
  The special `rainbow` color (used on the Challenger map's goal zone) is
  rendered as a multicolor gradient circle rather than a single flat color.
- **Connections are drawn as lines**, labeled with their traffic capacity;
  a connection currently being crossed is highlighted (thicker, bright
  yellow) versus an idle one (thin, dark) — making it easy to spot exactly
  which link is the current bottleneck.
- **Smooth interpolated movement**: drones glide between zones instead of
  teleporting once per turn, which makes the schedule far easier to follow in
  real time than reading raw text output.
- **A drone icon** is drawn either from a custom PNG (`assets/drone.png`) if
  present, or procedurally as a small vector icon (rotor arms and four
  motors) if the asset is missing — the visualizer never crashes for lack of
  an image file.
- **Automatic spreading** of drones that would otherwise overlap exactly
  (for instance, several drones waiting together at the start zone) into a
  small circular pattern, so individual drone IDs stay readable.
- **A turn counter and status HUD** at the top of the screen (current turn /
  total turns, running or paused).
- **Interactive playback controls** — `Space` to pause or resume, and the
  right arrow (or `P`) to manually step forward one turn at a time — useful
  for pausing exactly on a turn of interest during a peer-review walkthrough.
- **An optional background image** (`assets/background.jpg`), with a
  graceful fallback to a plain solid color if the file is missing or fails to
  load, so the visualizer works out of the box with zero required assets.

Together, these turn an abstract log such as `D1-mid D2-corridorA` into
something that can be watched, paused, and explained live — which is
particularly useful given that the subject explicitly warns that a peer
reviewer "may ask you to explain your code."

---

## Resources

### Documentation & References

- Python `heapq` — <https://docs.python.org/3/library/heapq.html>
- Python `re` module — <https://docs.python.org/3/library/re.html>
- Python regular expression HOWTO — <https://docs.python.org/3/howto/regex.html>
- Python `typing` — <https://docs.python.org/3/library/typing.html>
- Python `enum` — <https://docs.python.org/3/library/enum.html>
- Pygame documentation — <https://www.pygame.org/docs/>
- mypy documentation — <https://mypy.readthedocs.io/en/stable/>
- flake8 documentation — <https://flake8.pycqa.org/en/latest/>
- Dijkstra's algorithm — Cormen, Leiserson, Rivest & Stein, *Introduction to
  Algorithms*, chapter on single-source shortest paths; also Wikipedia:
  <https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm>
- For further background on cooperative pathfinding, see "Multi-Agent Path
  Finding (MAPF)" and "Prioritized Planning" — useful search terms for
  understanding the trade-offs between sequential and fully joint multi-agent
  search.

### AI Usage

AI assistance (an Anthropic Claude model) was used for the following,
specific tasks:

- **Reviewing and correcting the `Makefile`** — making the `install`, `run`,
  `debug`, and `lint` targets consistently use the virtual environment
  created by `make install`, instead of silently falling back to the system
  Python interpreter.
- **Explaining the existing pathfinding implementation** in `router.py`: the
  space-time graph model, the Dijkstra search loop, the Big-O complexity
  derivation, and the reasoning behind `heapq`'s `O(log n)` push/pop cost.
- **Explaining the regular expressions** used in `parser.py`, token by token.
- **Hardening `parser.py`'s metadata validation** — identifying and fixing a
  series of parsing edge cases (unknown metadata keys silently ignored,
  duplicate keys within the same bracket, non-positive capacity values,
  nested brackets, and invalid color names) that the original implementation
  did not reject, in line with the subject's requirement that any invalid
  input produce a clear, line-numbered error rather than being silently
  accepted.

This assistance was used strictly as a learning aid — to understand
*already-written* code, to identify and reason through edge cases in
existing logic, and to help structure documentation — not to generate new
application logic wholesale. This section should be reviewed and extended by
nrajaoar to reflect the complete, accurate picture of any AI assistance used
across the whole project, in line with the transparency expectations set out
in the subject's AI Instructions chapter (Chapter II).