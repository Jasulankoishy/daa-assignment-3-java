# Assignment 3: Graph Algorithms for a Campus Festival

Language: Java 17  
Repository: `Jasulankoishy/daa-assignment-3-java`

## 1. Running the project

Run these commands from the repository root:

```bash
python tools/run.py --setup
python tools/run.py --check
python tools/run.py --input tests/my_cases.jsonl
python tests/bench.py --update-analysis
```

The setup command checks the environment. The check command runs the public cases, while the input option runs a separate JSONL file. The benchmark script compares Kruskal and Prim and updates the benchmark section.

For manual compilation and execution:

```bash
javac -d out src/Java/*.java
java -cp out Main < input.jsonl
```

The project requires JDK 17 or newer. The Python runner requires Python 3.12 or newer.

## 2. Implementation choices

Each algorithm keeps its working arrays and collections inside the method call. This avoids carrying state from one input request into the next. A useful check is to run the same mixed batch twice in one Java process and compare the results.

The DFS-based algorithms use explicit stacks instead of recursive calls. Each vertex has a `next[v]` index that records which outgoing edge to examine next. When DFS returns to a vertex, it continues from that index. This keeps the traversal linear and avoids a stack overflow on a chain of 100,000 vertices.

Adjacency arrays retain the original input edge IDs. Sorting edges for Kruskal or building adjacency lists therefore does not change the IDs returned in the result.

Costs and distances use `long`. With up to 100,000 edges in a path or forest and weights of magnitude up to 10^9, a total can reach 10^14. Unreachable DAG vertices use `null`, since a negative value such as `-1` can be a valid distance.

## 3. Disjoint-set union

Initially, every vertex is its own component: `parent[i] = i` and `size[i] = 1`. The component count starts at `n`, and the largest component has size 1 when `n > 0`, or 0 otherwise.

For each pair `[u, v]`, the algorithm finds both roots. If they differ, it attaches the smaller tree to the larger tree, updates the root's size, and decreases the component count. It then records the current component count and largest size. A repeated union or a self-union leaves both values unchanged.

`find` is iterative. It first walks to the root, then walks through the same path again and makes each visited vertex point directly to that root.

The key invariant is that each parent tree represents exactly one connected component. The size stored at its root is the number of vertices in that component. A successful union merges two such components and adds their sizes, so the invariant is preserved after every operation.

With path compression and union by size, the amortised running time is `O(n + q α(n))`. Space is `O(n + q)` including the output states.

Cases to check include no operations, repeated pairs, self-unions, and a long sequence of unions. For `n = 0`, the valid empty operation sequence produces an empty result.

## 4. Kruskal's algorithm

Kruskal sorts edges by weight while retaining their original IDs. It then processes them in that order. An edge is selected only when its endpoints belong to different DSU components. Its weight is added to the total, and the two components are merged.

The selected edges always form a forest. To justify a new selection, consider one of the current DSU components as a cut. No lighter edge crossing that cut could have been skipped earlier: if its endpoints are in different components now, they were also in different components when that edge was processed. The selected edge is therefore a lightest crossing edge, and the cut property makes it safe to add.

Self-loops are skipped because both endpoints have the same root. Parallel edges are handled by the same rule. Negative weights require no special treatment; the algorithm only depends on their sorted order.

If `k` edges are selected, the forest has `n - k` components, including isolated vertices. An empty graph has cost 0 and no selected edges.

Sorting dominates the running time, giving `O(n + m log(m + 1))` time and `O(n + m)` space.

## 5. Prim's algorithm

Prim starts from an unvisited vertex and grows a tree using a minimum heap. After visiting a vertex, it adds that vertex's outgoing adjacency entries to the heap. Each entry stores the weight, original edge ID, and destination. Entries whose destinations are already visited are discarded when popped.

The heap contains all edges crossing from the current visited set to unvisited vertices, along with entries that have become stale. The first valid entry popped is a lightest edge across that cut. By the cut property, adding it preserves the possibility of completing a minimum spanning tree of the component.

When the heap becomes empty, the current component is finished. The outer loop starts again at the next unvisited vertex. This restart is necessary for disconnected graphs; an isolated vertex counts as a component without adding an edge.

Each adjacency entry is pushed at most once. The lazy-heap implementation takes `O(n + m log(m + 1))` time and `O(n + m)` space. Kruskal and Prim should return the same total cost and component count, although equal-weight edges may lead to different selected IDs.

## 6. Strongly connected components

Kosaraju's algorithm uses the graph and its transpose. The first DFS pass records vertices when they finish. The second pass visits the transpose in reverse finishing order and assigns one component label to each DFS tree.

For an edge from SCC `A` to a different SCC `B`, the maximum finishing time in `A` is greater than the maximum finishing time in `B`. The next unlabeled vertex in reverse finishing order therefore belongs to a source component among the remaining SCCs. In the transpose, that component cannot reach another unlabeled component. The second DFS collects exactly its vertices.

To construct the condensation graph, scan the original edges. For each edge whose endpoints have different labels, insert the component pair into a hash set. This removes duplicate condensation edges and excludes internal edges and self-loops.

Both DFS passes are iterative. The expected running time is `O(n + m)`, including hash-set operations, and space is `O(n + m)`.

Useful cases include an empty graph, isolated vertices, a single directed cycle, duplicate edges, and a chain of 100,000 vertices.

## 7. Topological sorting

The DFS traversal gives each vertex one of three states:

- `0`: not visited;
- `1`: active on the DFS stack;
- `2`: finished.

When scanning `v -> w`, an unvisited `w` is pushed onto the stack. An edge to an active vertex reveals a directed cycle: the stack already contains a path from that vertex to `v`. An edge to a finished vertex does not indicate a cycle.

Once all outgoing edges of `v` have been examined, `v` is marked finished and appended to the finishing list. If no cycle is found, reversing this list gives a topological order. For every edge `u -> v`, `v` finishes before `u`, so `u` appears first in the reversed list.

DFS starts from every unvisited vertex, which also covers disconnected graphs. A self-loop is a cycle. For an empty graph, the result is an empty order with `acyclic = true`.

The traversal takes `O(n + m)` time and `O(n + m)` space including adjacency storage.

## 8. Shortest paths in a DAG

First, compute a topological order of the entire graph. If any component contains a directed cycle, return `acyclic = false` with empty distance and parent arrays, even if that cycle is unreachable from the source.

Otherwise, initialise every distance to `null` and every parent edge to `-1`, then set the source distance to 0. Process vertices in topological order. Skip unreachable vertices. For each outgoing edge `(u, v, w)`, update `dist[v]` when it is unset or when `dist[u] + w` is smaller, and store the original edge ID in `parent_edge[v]`.

When a vertex is processed, every possible predecessor has already been processed. All candidate paths into it have therefore been considered, and its distance is final. This also explains why negative weights work: there are no cycles, and each edge is relaxed after its starting vertex's distance is final.

The running time and space are both `O(n + m)`.

### Reconstructing a path

An unreachable target has no path. If the target is the source, the path is `[source]`. Otherwise, start at the target and repeatedly read `parent_edge[v]`, then move to the starting vertex of that edge. Stop at the source and reverse the collected vertices.

For a path with `L` vertices, reconstruction takes `O(L)` time and output space.

For example:

```text
n = 5, source = 0
edges = [[0,1,3], [0,2,8], [1,2,-7], [2,3,4]]

distance    = [0, 3, -4, 0, null]
parent_edge = [-1, 0, 2, 3, -1]
```

The path to vertex 3 is `0 -> 1 -> 2 -> 3`, using edge IDs `0, 2, 3`. Its cost is `3 - 7 + 4 = 0`. Vertex 4 is unreachable.

Equal-cost paths can produce different valid parent arrays. For example:

```text
n = 3, source = 0
edges = [[0,1,5], [0,1,5], [1,2,1], [0,2,6]]
```

Both `0 -> 2` and `0 -> 1 -> 2` cost 6. Either is a correct shortest path. Tests should validate the distance and reconstructed path instead of requiring one particular parent array.

## 9. Testing

The results need semantic checks because several algorithms can return more than one correct answer.

- For a minimum spanning forest, selected IDs must be distinct and valid. The edges must contain no cycles, their weights must sum to the reported cost, and their count must equal `n - components`. The forest must also span every original connected component. Compare its cost with an independent reference result.
- For SCCs, compare the partition with a reference partition without relying on numeric label values. The condensation edges must be exactly the distinct pairs induced by original edges between different components.
- For a topological order, every vertex must appear once and every edge `u -> v` must satisfy `pos[u] < pos[v]`. A cycle result should agree with an independent cycle check.
- For DAG shortest paths, compare distances with a reference result. Each reachable non-source vertex must have a valid parent edge ending at that vertex, satisfy the distance equation, and have a parent chain that reaches the source. Unreachable vertices must have distance `null`.

The test set should cover empty and disconnected graphs, isolates, self-loops, parallel edges, equal weights, negative weights, and totals above the 32-bit integer range. DAG tests should include a cycle outside the source's reachable component.

Large cases should include a 100,000-vertex chain and inputs at the stated limits of 100,000 vertices and 250,000 edges or union operations. Repeating a mixed batch in one process checks that requests do not share mutable state.

The supplied draft describes a public suite of 36 cases, but does not include its execution output. A passing result should be recorded only after running:

```bash
python tools/run.py --check
```

## 10. Kruskal versus Prim

Both implementations have an `O(n + m log(m + 1))` time bound. Kruskal sorts the edges once and then performs DSU operations. Lazy Prim builds adjacency lists and performs heap operations while growing each component. Both use `O(n + m)` space, but their allocation and access patterns differ, so the asymptotic bounds alone do not determine which is faster on these inputs.

No measured timings were included in the supplied draft. To complete the comparison, run both algorithms on the same graphs at three input sizes, check that their costs and component counts agree, and record the benchmark environment and timings.

<!-- BENCH:START -->
Benchmark measurements pending. Run `python tests/bench.py --update-analysis`.
<!-- BENCH:END -->

## 11. Sources and AI assistance

The algorithms follow the course material and standard descriptions in Cormen, Leiserson, Rivest, and Stein, *Introduction to Algorithms*: disjoint sets, minimum spanning trees, DFS, strongly connected components, and shortest paths in DAGs.

AI tools, including Claude, were used to help explain and edit the analysis. The analysis alone does not establish who wrote the implementation or which tests were run; those claims should be supported by the code and recorded test results.
