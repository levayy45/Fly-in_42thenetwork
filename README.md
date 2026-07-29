*This project has been created as part of the 42 curriculum by levayy.*

# Fly-in

## Description

Fly-in routes a fleet of drones from a central base (`start_hub`) to a
target location (`end_hub`) across a network of connected zones, in as
few simulation turns as possible.

The map format describes zones with coordinates, a behavioural type and
an occupancy limit, plus bidirectional connections with their own
capacity. Zones cost one turn to enter, except `restricted` zones which
cost two and `blocked` zones which cannot be entered at all. Only one
drone fits in a zone unless `max_drones` says otherwise, and only one
drone crosses a connection per turn unless `max_link_capacity` says
otherwise.

The program is written in Python 3.10+, is fully object-oriented, passes
`flake8` and `mypy --strict`, and implements all of its graph logic by
hand: no `networkx`, no `graphlib`, no external solver.

## Instructions

```bash
make install                 # install flake8, mypy and pytest
make run                     # run on the default map, with visuals
make run MAP=maps/valid/hard_2_capacity.map
make lint                    # flake8 + mypy with the mandatory flags
make lint-strict             # flake8 + mypy --strict
make test                    # the pytest suite (70 tests)
make bench                   # solve every map, compare to the targets
make debug MAP=...           # run under pdb
make clean                   # remove caches and bytecode
```

Direct invocation:

```bash
python3 main.py <map_file> [options]

  -v, --visual    coloured network, chosen routes and turn-by-turn board
  -m, --metrics   score and secondary metrics
      --verify    replay the output and assert every rule is respected
  -q, --quiet     hide the plain movement lines
      --no-color  disable ANSI colours
```

With no option the program prints **only** the mandated output format:
one line per turn, movements separated by spaces.

## Usage example

Input — `maps/valid/easy_2_fork.map`:

```
nb_drones: 4

start_hub: start 0 0 [color=green]
end_hub: goal 8 0 [color=red]
hub: junction 3 0 [color=yellow max_drones=2]
hub: path_a 5 2 [color=blue]
hub: path_b 5 -2 [color=blue]

connection: start-junction [max_link_capacity=2]
connection: junction-path_a
connection: junction-path_b
connection: path_a-goal
connection: path_b-goal
```

Output:

```
$ python3 main.py maps/valid/easy_2_fork.map
D1-junction D2-junction
D1-path_a D2-path_b D3-junction D4-junction
D1-goal D2-goal D3-path_a D4-path_b
D3-goal D4-goal
```

Four drones delivered in four turns. `junction` holds two drones at once
and the link feeding it carries two per turn, so the fleet flows through
in two waves of two.

A drone crossing towards a `restricted` zone is reported with the name of
the connection it occupies, then with the zone it lands on:

```
$ python3 main.py maps/valid/medium_3_priority.map
D1-fast_junction D4-start-slow_path_1
D4-slow_path_1 D1-fast_path D2-fast_junction ...
```

`D4-start-slow_path_1` means drone 4 is in flight on the connection
`start-slow_path_1`; it lands on `slow_path_1` the following turn.

## Features

- Strict parser with located error messages (`line N: cause`).
- Hand written Dijkstra with priority-aware tie breaking.
- Hand written min-cost max-flow for multi-route planning.
- Turn engine enforcing zone capacity, link capacity, multi-turn
  crossings and strategic waiting, with deadlock detection.
- Independent verifier that replays the printed output and rejects any
  illegal run (`--verify`).
- Coloured terminal visualisation and secondary metrics.
- 10 valid maps and 18 deliberately broken maps for error handling.
- 70 unit and end-to-end tests.

## Algorithm choices and implementation strategy

### 1. Cost model

Movement cost is paid on **entering** a zone, so a route's cost is the
sum of the entry costs of every zone after the start hub. `normal` and
`priority` cost 1, `restricted` costs 2, `blocked` is excluded from the
graph entirely.

`priority` zones must be *preferred* without being *cheaper* in turns.
Every cost is therefore scaled by `weight = number_of_zones + 1` and a
priority zone gets a one unit rebate. A simple route visits at most
`number_of_zones` zones, so the rebates of a whole route always sum to
less than one scaled turn: a slower route can never look cheaper than a
faster one, and the rebate only ever breaks ties. This is in
`pathfinder.py`.

### 2. Choosing the routes — minimum cost flow

One shortest route is not enough: a single route delivers `N` drones in
`cost + N - 1` turns, while several routes used in parallel finish much
sooner. Choosing *which* routes can be used simultaneously is a flow
problem, because zone and link capacities are exactly flow capacities.

`router.py` builds the flow network as follows.

- Every zone is split into an **in** node and an **out** node joined by
  an arc whose capacity is the zone's `max_drones`. Splitting is the
  standard way to express a *vertex* capacity in an edge-capacitated
  flow problem; the start and end hubs get an unbounded arc.
- Every connection becomes one arc per direction with capacity
  `max_link_capacity`, and a cost equal to the scaled entry cost of the
  zone it leads into.
- Source is the start hub's out node, sink is the end hub's in node.

The flow is then augmented **one unit at a time** by the successive
shortest path algorithm (`flow.py`), using a queue based Bellman-Ford
(SPFA) rather than Dijkstra because residual arcs carry negative costs.
After each augmentation the flow is decomposed into concrete routes.
Two properties fall out of this construction:

- the `k` routes obtained are simultaneously usable *by construction*,
  since the flow respects every capacity;
- they are the **cheapest** such set of `k` routes, since each
  augmentation followed a minimum cost path.

### 3. Distributing the fleet

For each candidate width `k`, drones are assigned greedily: the next
drone goes to the route minimising `cost + already_assigned`. That is
the classic argument that a route of cost `c` fed one drone per turn
finishes its `d` drones on turn `c + d - 1`, so balancing those values
balances the finish times.

More routes is not always better — a long detour can finish later than
waiting for a short route. So every width is kept as a candidate.

### 4. Simulating and picking the winner

`simulator.py` executes a plan turn by turn and is the single authority
on legality:

- drones are processed **closest to the goal first**, which is what
  makes the rule "a drone leaving a zone frees its slot during the same
  turn" usable: the drone behind sees the freed slot immediately;
- a drone heading for a `restricted` zone **reserves** its landing slot
  before departing, so it is guaranteed to land on schedule and can
  never be forced to wait on a connection;
- a drone that lands from a crossing has already used its movement for
  that turn and is not offered a second one;
- if a whole turn passes with no movement the plan is rejected as a
  deadlock instead of looping forever.

`PlanSelector` simulates every candidate width and keeps the run with
the lowest turn count. The heuristic estimate is only used for ordering,
never for pruning, so a better plan is never skipped.

### 5. Complexity and memory

Let `Z` be the number of zones, `E` the number of connections and `N` the
number of drones.

| Stage | Complexity |
|---|---|
| Parsing | `O(Z + E)` |
| Dijkstra | `O((Z + E) log Z)` |
| One flow augmentation (SPFA) | `O(Z * E)` worst case |
| Planning, all widths | `O(min(N, maxflow) * Z * E)` |
| One simulated turn | `O(N * Z)` |
| Full selection | `O(min(N, maxflow) * turns * N * Z)` |

Memory is `O(Z + E + N)`: the adjacency list, the residual graph (two
arcs per connection per direction, two nodes per zone) and one object
per drone. Routes are computed **once** per candidate width and cached
inside the `RoutePlan`; the simulator never recomputes a path, it only
walks the precomputed route, so no pathfinding happens inside the turn
loop.

Measured: 1000 drones on a two-hop map plan and simulate in about 0.7 s;
200 drones on the challenger map in about 0.2 s.

## Visual representation

`renderer.py` defines an abstract `Renderer` with two implementations, so
the entry point never branches on whether colours are wanted.

- `PlainRenderer` prints strictly the mandated format and nothing else,
  which is what a grading script consumes.
- `TerminalRenderer` (`--visual`) adds three views:
  - the **network view**: every zone with its type, entry cost, capacity
    and coordinates, painted with the colour declared in the map file
    (falling back to a colour per zone type when none is given), plus
    every connection with its capacity;
  - the **routes view**: the routes the planner chose, their cost and how
    many drones each one carries — this is what makes the planner's
    decision auditable at a glance;
  - the **simulation view**: each turn with a progress bar of drones
    delivered so far, next to that turn's movements.

`--metrics` prints the primary score (total turns) and the secondary
metrics from the subject: movements, movements per turn, average turns
per drone and total path cost.

Why this helps: the plain format tells you *what* happened, the routes
view tells you *why*, and the progress bar shows where the throughput
plateaus — which is exactly where a capacity bottleneck sits.

`--no-color` disables ANSI escapes for logs and pipes.

## Benchmarks

`make bench` on the shipped maps:

| Map | Drones | Turns | Target |
|---|---|---|---|
| easy_1_linear | 2 | 5 | ≤ 6 |
| easy_2_fork | 4 | 4 | ≤ 8 |
| easy_3_capacity | 4 | 2 | ≤ 6 |
| medium_1_deadend | 5 | 5 | ≤ 12 |
| medium_2_loop | 6 | 5 | ≤ 15 |
| medium_3_priority | 5 | 7 | ≤ 12 |
| hard_1_maze | 8 | 8 | ≤ 30 |
| hard_2_capacity | 12 | 17 | ≤ 35 |
| hard_3_ultimate | 15 | 11 | ≤ 45 |
| challenger_impossible_dream | 25 | 14 | record 45 |

These maps were written for this repository from the topologies and
targets described in the subject; the official map files were not part
of the material available here. Re-run `make bench` after dropping the
official maps into `maps/valid/` and adjust the targets in
`benchmark.py`.

## Technical choices

- **Object-oriented throughout.** Each concept is a class with a single
  responsibility: `Zone`, `Connection`, `Network`, `Metadata`,
  `MapParser`, `ShortestPathFinder`, `MinCostFlow`, `Router`,
  `RoutePlan`, `Drone`, `Simulator`, `PlanSelector`,
  `SimulationVerifier`, `Renderer` and its subclasses, `Application`.
  State is private with read-only properties; the enums `ZoneType`,
  `ZoneRole` and `DroneState` replace magic strings.
- **Fully typed.** Passes `mypy --strict`. `Zone.capacity` returns
  `int | None`, where `None` means unlimited, so "no limit" cannot be
  confused with "limit zero".
- **Errors are values, not crashes.** Every failure raises a subclass of
  `FlyInError`; `main.py` catches that one base type plus `OSError` and
  exits with status 1 and a readable message. Files are read through a
  context manager. No unhandled exception should ever reach the user.
- **The verifier is deliberately separate.** It shares no code path with
  the simulator, so it is a real check rather than a tautology.

## Project layout

```
main.py         CLI entry point (Application)
parser.py       map file -> Network, with located errors
metadata.py     [key=value] block parsing
zone.py         ZoneType, ZoneRole, Zone
connection.py   Connection
network.py      the graph: zones, links, adjacency
pathfinder.py   Dijkstra with priority tie breaking
flow.py         min-cost max-flow (SPFA augmentation)
router.py       flow -> routes -> RoutePlan candidates
drone.py        Drone and its state machine
simulator.py    turn engine, PlanSelector
verifier.py     independent replay of the output
renderer.py     PlainRenderer and TerminalRenderer
benchmark.py    solve every map, compare to targets
errors.py       exception hierarchy
maps/valid/     10 solvable maps
maps/invalid/   18 maps covering the parser error paths
tests/          pytest suite
```

## Resources

- Cormen, Leiserson, Rivest, Stein, *Introduction to Algorithms* —
  shortest paths (Dijkstra, Bellman-Ford) and maximum flow.
- Ahuja, Magnanti, Orlin, *Network Flows* — successive shortest paths
  for minimum cost flow, and node splitting for vertex capacities.
- Competitive Programming Algorithms (cp-algorithms.com) — SPFA and
  min-cost-flow reference implementations.
- Python documentation: `typing`, `enum`, `abc`, `argparse`,
  `collections.Counter`, `heapq`.
- PEP 8, PEP 257, PEP 484 — style, docstrings and type hints.
- flake8 and mypy documentation.

### Use of AI

An AI assistant was used on this project for:

- discussing the design before coding: how to express a *zone* capacity
  in an edge-capacitated flow problem (node splitting), and how to make
  `priority` zones preferred without changing turn counts (the scaled
  cost with a one unit rebate);
- reviewing the turn engine for rule violations, which is how the
  double-movement bug was found: a drone landing from a `restricted`
  crossing was still being offered a second move in the same turn. That
  led to writing `verifier.py` as an independent check;
- drafting docstrings and this README.

Every algorithmic decision above was reviewed line by line, the maps and
the tests were written to attack the implementation rather than to
confirm it, and the whole suite runs under `flake8` and `mypy --strict`.
