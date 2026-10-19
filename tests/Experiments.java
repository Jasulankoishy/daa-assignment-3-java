import java.util.*;

/** Direct helper calls and measured algorithm invocations, outside JSON transport. */
public final class Experiments {
    private static Map<String, Object> request(int n, int[][] edges, int source) {
        List<List<Integer>> rows = new ArrayList<>();
        for (int[] edge : edges) rows.add(List.of(edge[0], edge[1], edge[2]));
        return Map.of("n", n, "edges", rows, "source", source);
    }

    private static void require(boolean condition, String reason) {
        if (!condition) throw new AssertionError(reason);
    }

    private static void routeCase(String name, int n, int[][] edges, int source,
                                  int target, List<Integer> expected) {
        Map<String, Object> result = Algorithms.dag(request(n, edges, source));
        Long[] distance = (Long[]) result.get("distance");
        int[] parents = (int[]) result.get("parent_edge");
        List<Integer> route = Algorithms.reconstructRoute(source, target, distance, parents, edges);
        require(route.equals(expected), name);
        List<Integer> ids = new ArrayList<>();
        long total = 0;
        for (int i = 1; i < route.size(); i++) {
            int id = parents[route.get(i)];
            require(edges[id][0] == route.get(i-1) && edges[id][1] == route.get(i), "edge direction");
            ids.add(id);
            total += edges[id][2];
        }
        require(route.isEmpty() ? distance[target] == null : total == distance[target], "route weight");
        Map<String, Object> log = new LinkedHashMap<>();
        log.put("case", name); log.put("source", source); log.put("target", target);
        log.put("edges", edges); log.put("distance", distance); log.put("parent_edge", parents);
        log.put("call", "Algorithms.reconstructRoute(source, target, distance, parentEdge, edges)");
        log.put("route", route); log.put("selected_edge_ids", ids);
        log.put("route_cost", route.isEmpty() ? null : total);
        log.put("passed", true);
        System.out.println(Json.write(log));
    }

    private static void routes() {
        int[][] edges = {{0,1,3},{0,2,8},{1,2,-7},{2,3,4}};
        routeCase("reachable", 5, edges, 0, 3, List.of(0,1,2,3));
        routeCase("source", 5, edges, 0, 0, List.of(0));
        routeCase("unreachable", 5, edges, 0, 4, List.of());
        routeCase("parallel and tied", 4, new int[][]{{0,1,2},{0,1,2},{0,2,2},{1,3,1},{2,3,1}},
                0, 3, List.of(0,2,3));
        routeCase("parallel edge target", 2, new int[][]{{0,1,2},{0,1,2}},
                0, 1, List.of(0,1));
    }

    // The negative backbone is already a tree. Every extra edge is nonnegative,
    // so each backbone edge is strictly cheapest across its corresponding cut.
    private static int[][] graph(int n, int m, long seed) {
        Random random = new Random(seed);
        int[][] edges = new int[m][3];
        for (int i = 0; i < n-1; i++) edges[i] = new int[]{i, i+1, -1-random.nextInt(1000)};
        for (int i = n-1; i < m; i++)
            edges[i] = new int[]{random.nextInt(n), random.nextInt(n), random.nextInt(1001)};
        return edges;
    }

    private static void forest(int n, int[][] edges, Map<String, Object> answer) {
        List<?> ids = (List<?>) answer.get("edge_ids");
        require(ids.size() == n-1 && ((Number) answer.get("components")).intValue() == 1, "forest size");
        boolean[] selected = new boolean[edges.length];
        long cost = 0, optimum = 0;
        for (int i = 0; i < n-1; i++) optimum += edges[i][2];
        for (Object value : ids) {
            int id = ((Number) value).intValue();
            require(id >= 0 && id < n-1 && !selected[id], "expected backbone tree witness");
            selected[id] = true; cost += edges[id][2];
        }
        require(cost == optimum && ((Number) answer.get("cost")).longValue() == optimum, "optimum cost");
    }

    private static Map<String, Object> invoke(boolean prim, Map<String, Object> input) {
        return prim ? Algorithms.prim(input) : Algorithms.kruskal(input);
    }

    private static void benchmark() {
        int[][] sizes = {{1000,5000},{10000,50000},{100000,250000}};
        for (int[] size : sizes) {
            int n = size[0], m = size[1];
            long seed = 31019L + n;
            int[][] edges = graph(n, m, seed);
            Map<String, Object> input = request(n, edges, 0);
            // Validate before timing; then warm both methods on this same graph.
            forest(n, edges, Algorithms.kruskal(input));
            forest(n, edges, Algorithms.prim(input));
            for (int warm = 0; warm < 5; warm++) {
                invoke(false, input); invoke(true, input);
            }
            double[][] milliseconds = new double[2][5];
            for (int trial = 0; trial < 5; trial++) {
                // Alternate which method runs first to reduce order bias.
                for (int position = 0; position < 2; position++) {
                    int method = (trial + position) % 2;
                    long start = System.nanoTime();
                    Map<String, Object> answer = invoke(method == 1, input);
                    long stop = System.nanoTime();
                    milliseconds[method][trial] = (stop-start)/1_000_000.0;
                    forest(n, edges, answer);
                }
            }
            for (int method = 0; method < 2; method++) {
                double[] sorted = milliseconds[method].clone();
                Arrays.sort(sorted);
                System.out.println(Json.write(Map.of("method", method == 0 ? "kruskal" : "prim",
                        "n", n, "m", m, "seed", seed, "milliseconds", milliseconds[method],
                        "median_ms", sorted[2], "warmup_calls_per_method", 5,
                        "validated", true)));
            }
        }
    }

    public static void main(String[] args) {
        if (args.length == 1 && args[0].equals("benchmark")) benchmark();
        else routes();
    }
}
