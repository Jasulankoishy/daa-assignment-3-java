# Reproducible tests and measurements

Run all commands from the repository root. Java 17+ (`java` and `javac`) and Python 3.12+ must be on PATH. The supplied launcher compiles with `javac --release 17`.

```sh
python tools/run.py --setup
python tools/run.py --check
python tests/check_own.py
python tools/run.py --input tests/my_cases.jsonl
python tests/run_evidence.py
```

`run_evidence.py` executes all checks and replaces the saved evidence with the new run. It compiles `Experiments.java` separately from production code and runs helper tests and benchmarks. To run those directly after the public build:

```sh
javac --release 17 -encoding UTF-8 -cp .build/Java -d .build/Java tests/Experiments.java
java -Xmx384m -cp .build/Java Experiments
java -Xmx384m -cp .build/Java Experiments benchmark
```

On the recorded Windows machine the JDK was not on PATH. The session used:

```powershell
$env:Path = 'C:\Users\User\.jdks\openjdk-25.0.1\bin;' + $env:Path
python tests/run_evidence.py
```

Use your own JDK directory on another machine. The recorded runtime is OpenJDK 25.0.1; compilation targets Java 17. GitHub's supplied workflow runs Java 17.

## Files and expected answers

- `my_cases.jsonl`: 441 inputs, including fixed boundaries and seeded random cases.
- `results/expected.jsonl`: one independently calculated expectation per input. Non-unique witnesses are checked by properties, not exact array equality.
- `results/actual.jsonl`: 882 actual results: the input sequence twice, within one JVM.
- `check_own.py`: generator (`random.Random(31019)`), independent reference methods, semantic validators and scale checks.
- `results/witness_checks.jsonl`: two accepted witnesses and one rejected witness for forests, SCC, topo and DAG. The forest validator is shared by Kruskal and Prim.
- `results/scale_inputs.jsonl.gz`, `scale_actual.jsonl.gz`: complete large inputs and actual outputs, compressed to reduce repository size. Each line corresponds to the same line in the other file.
- `results/scale_summary.jsonl`: dimensions and pass results for all eight large cases.
- `Experiments.java`, `results/routes.jsonl`: actual helper calls, arrays, vertex routes, selected edge IDs, edge direction and cost checks.
- `results/benchmark.jsonl`: all five measurements per method per size, medians, seeds and warm-up count.
- `results/environment.json`: runtime, OS, CPU, physical RAM, timer, timing boundary and limitations.
- `results/setup.txt`, `public.txt`, `own.txt`: captured check output; companion stderr files preserve diagnostics.

### Independent justification

For small DSU cases the reference relabels every vertex in a merged component, then counts labels. It does not use the production DSU implementation.

For small forests, Floyd-Warshall computes undirected reachability. The reference exhaustively enumerates subsets of exactly `n-components` original edges and keeps those with precisely the input connectivity. Such a connected-per-component subset of that size is a spanning forest; minimum weight among all such subsets is the optimum. Validation also checks ID uniqueness, range and summed weight. At most nine edges are generated in each random case, keeping exhaustive search bounded.

For SCC, the reference computes transitive closure. Two vertices must have the same label exactly when they are mutually reachable. Cross-label pairs from input edges must equal the reported condensation with no duplicates.

For topo and DAG, the independent cycle test asks whether any edge `u -> v` has a return path `v -> u` in the transitive closure. A valid topological witness must be a vertex permutation and place every edge forward. DAG distances are computed by Bellman-Ford relaxation, independently of the production topological algorithm. Every reported parent path must follow incoming original edges, reach the source without repetition and have the expected total weight.

Fixed cases include empty graphs, isolates, repeated/self unions, loops, parallel/tied edges, a diamond DAG, duplicate condensation edges, negative weights, a valid distance of -1, unreachable vertices, an unreachable cycle, singleton DAG and sums of 3,000,000,000. Random cases add varied combinations; extra acyclic random inputs exercise distances.

### Full-limit cases

The first six large cases use `n=100000`, `m` or `q=250000`: a chain `0 -> 1 -> ... -> 99999`, followed by repeated chain edges. These have simple independent answers:

- DSU: after operation i (zero based), the first 99999 operations yield `[99999-i, i+2]`; subsequent operations yield `[1,100000]`.
- Kruskal/Prim: every adjacent pair must be connected once. All edge weights are -1,000,000,000, so the cost is -99,999,000,000,000 and there is one component. Selected IDs must represent every chain link exactly once.
- SCC: every vertex has its own label and condensation is the chain with duplicates removed.
- Topo: the only possible order is `[0,1,...,99999]`.
- DAG: distance to v is `-v * 1000000000`, and each non-source parent must be an original edge from `v-1` to `v`.

Case 7 closes the chain into a 100000-vertex directed ring: one SCC, no condensation edges. Case 8 leaves source 0 isolated and puts vertices 1..99999 in a directed cycle: `acyclic=false` and empty result arrays. Each large request runs through the supplied JSON adapter with a 384 MiB JVM heap and the launcher's 20-second request timeout.

### Route helper

`reconstructRoute` returns an empty list for an unreachable target and `[source]` for the source. The five direct calls verify reachable, source, unreachable, and tied/parallel-edge behavior. The additional parallel-target call reconstructs [0,1] using edge ID 0; the tied target-3 route is `[0,2,3]` with IDs `[2,4]`. Different valid shortest witnesses are allowed by the task contract.

### Benchmark protocol

The same graph is passed to both algorithms at each size: 1000/5000, 10000/50000 and 100000/250000 (vertices/edges). `java.util.Random(31019+n)` generates a negative-weight chain and nonnegative extra edges. The chain is the unique optimal tree: across every chain-edge cut it is strictly cheaper than all extra edges. Validation checks that each returned forest contains exactly those original chain IDs, without repetition, and has their summed weight. This check happens before warm-up and after each measured invocation, outside the timed interval.

There are five warm-up calls per method per size, followed by five measured calls. Trial order alternates. `System.nanoTime()` measures complete calls to `Algorithms.kruskal` or `Algorithms.prim`, including input conversion to arrays, sorting/adjacency construction and result packaging. Graph generation, JSON parsing, JVM startup, compilation, validation and output are excluded for both methods. These structured inputs are reproducible, but not representative of every graph family. Desktop load, JIT and GC can affect results. Raw observations are saved without claiming universal speed superiority.

## Authorship and remaining submission work

Codex (OpenAI) generated the Java implementation, additional tests, benchmark harness and this test documentation, and executed the recorded checks. The starter adapters, public checker and assignment requirements come from the RZhaniya/daa-assignment-3-graphs template. No external graph library is used.

The student will write the English root `ANALYSIS.md` independently and acknowledge the actual assistance under the course syllabus. It still needs the required algorithm explanations, invariants, correctness arguments, boundaries and complexity; state reset/deep DFS; actual helper evidence; benchmark data and interpretation; environment, commands and sources. This test README and recorded data do not replace that report. Add the completed report before submitting the final commit URL to Moodle.

