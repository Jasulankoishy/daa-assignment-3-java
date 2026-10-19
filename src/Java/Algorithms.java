import java.util.*;

public final class Algorithms {
    private Algorithms() { }

    // Negative entries store component sizes; other entries store parents.
    private static final class Partition {
        final int[] link;
        int components, largest;
        Partition(int n) {
            link = new int[n];
            Arrays.fill(link, -1);
            components = n;
            largest = n == 0 ? 0 : 1;
        }
        int root(int vertex) {
            int representative = vertex;
            while (link[representative] >= 0) representative = link[representative];
            while (vertex != representative) {
                int next = link[vertex];
                link[vertex] = representative;
                vertex = next;
            }
            return representative;
        }
        boolean join(int a, int b) {
            a = root(a); b = root(b);
            if (a == b) return false;
            if (link[a] > link[b]) { int swap = a; a = b; b = swap; }
            link[a] += link[b];
            link[b] = a;
            components--;
            largest = Math.max(largest, -link[a]);
            return true;
        }
    }

    // Each vertex owns a contiguous slice of the original edge IDs.
    private static final class Adjacency {
        final int[] offset, edgeId, destination;
        Adjacency(int n, int[][] edges, boolean reverse, boolean undirected) {
            offset = new int[n + 1];
            for (int[] edge : edges) {
                offset[(reverse ? edge[1] : edge[0]) + 1]++;
                if (undirected) offset[edge[1] + 1]++;
            }
            for (int v = 0; v < n; v++) offset[v + 1] += offset[v];
            edgeId = new int[offset[n]];
            destination = new int[offset[n]];
            int[] cursor = offset.clone();
            for (int id = 0; id < edges.length; id++) {
                int from = edges[id][reverse ? 1 : 0], to = edges[id][reverse ? 0 : 1];
                int slot = cursor[from]++;
                edgeId[slot] = id; destination[slot] = to;
                if (undirected) {
                    slot = cursor[to]++;
                    edgeId[slot] = id; destination[slot] = from;
                }
            }
        }
    }

    static Map<String, Object> dsu(Map<String, Object> input) {
        Partition partition = new Partition(Input.vertexCount(input));
        int[][] operations = Input.operations(input);
        int[][] states = new int[operations.length][2];
        for (int i = 0; i < operations.length; i++) {
            partition.join(operations[i][0], operations[i][1]);
            states[i][0] = partition.components;
            states[i][1] = partition.largest;
        }
        return Map.of("states", states);
    }

    static Map<String, Object> kruskal(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int[][] edges = Input.edges(input);
        Integer[] sortedIds = new Integer[edges.length];
        for (int id = 0; id < edges.length; id++) sortedIds[id] = id;
        Arrays.sort(sortedIds, Comparator.comparingInt((Integer id) -> edges[id][2])
                .thenComparingInt(id -> id));
        Partition partition = new Partition(n);
        List<Integer> selected = new ArrayList<>();
        long cost = 0;
        for (int id : sortedIds) {
            if (partition.join(edges[id][0], edges[id][1])) {
                selected.add(id); cost += edges[id][2];
            }
        }
        return Map.of("cost", cost, "edge_ids", selected, "components", partition.components);
    }

    private record Frontier(int vertex, int edgeId, int weight) { }

    static Map<String, Object> prim(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int[][] edges = Input.edges(input);
        Adjacency graph = new Adjacency(n, edges, false, true);
        boolean[] visited = new boolean[n];
        PriorityQueue<Frontier> frontier = new PriorityQueue<>(
                Comparator.comparingInt(Frontier::weight).thenComparingInt(Frontier::edgeId));
        List<Integer> selected = new ArrayList<>();
        long cost = 0;
        int components = 0;
        for (int start = 0; start < n; start++) {
            if (visited[start]) continue;
            components++;
            frontier.add(new Frontier(start, -1, 0));
            while (!frontier.isEmpty()) {
                Frontier next = frontier.remove();
                int vertex = next.vertex();
                if (visited[vertex]) continue;
                visited[vertex] = true;
                if (next.edgeId() != -1) { selected.add(next.edgeId()); cost += next.weight(); }
                for (int slot = graph.offset[vertex]; slot < graph.offset[vertex + 1]; slot++) {
                    int to = graph.destination[slot], id = graph.edgeId[slot];
                    if (!visited[to]) frontier.add(new Frontier(to, id, edges[id][2]));
                }
            }
        }
        return Map.of("cost", cost, "edge_ids", selected, "components", components);
    }

    // A suspended DFS retains its next adjacency slot. null signals a cycle.
    private static int[] finishOrder(Adjacency graph, boolean rejectCycles) {
        int n = graph.offset.length - 1;
        byte[] state = new byte[n];
        int[] stack = new int[n], cursor = graph.offset.clone(), finished = new int[n];
        int count = 0;
        for (int start = 0; start < n; start++) {
            if (state[start] != 0) continue;
            int depth = 0;
            stack[depth++] = start; state[start] = 1;
            while (depth > 0) {
                int vertex = stack[depth - 1];
                if (cursor[vertex] == graph.offset[vertex + 1]) {
                    depth--; state[vertex] = 2; finished[count++] = vertex;
                    continue;
                }
                int to = graph.destination[cursor[vertex]++];
                if (state[to] == 1 && rejectCycles) return null;
                if (state[to] == 0) { state[to] = 1; stack[depth++] = to; }
            }
        }
        return finished;
    }

    static Map<String, Object> scc(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int[][] edges = Input.edges(input);
        int[] finished = finishOrder(new Adjacency(n, edges, false, false), false);
        Adjacency transpose = new Adjacency(n, edges, true, false);
        int[] component = new int[n], stack = new int[n];
        Arrays.fill(component, -1);
        int label = 0;
        for (int i = n - 1; i >= 0; i--) {
            int start = finished[i];
            if (component[start] != -1) continue;
            int depth = 0;
            stack[depth++] = start; component[start] = label;
            while (depth > 0) {
                int vertex = stack[--depth];
                for (int slot = transpose.offset[vertex]; slot < transpose.offset[vertex + 1]; slot++) {
                    int to = transpose.destination[slot];
                    if (component[to] == -1) { component[to] = label; stack[depth++] = to; }
                }
            }
            label++;
        }
        Set<Long> seen = new HashSet<>();
        List<int[]> condensation = new ArrayList<>();
        for (int[] edge : edges) {
            int from = component[edge[0]], to = component[edge[1]];
            long key = ((long) from << 32) | (to & 0xffffffffL);
            if (from != to && seen.add(key)) condensation.add(new int[]{from, to});
        }
        return Map.of("component", component, "condensation", condensation);
    }

    static Map<String, Object> topo(Map<String, Object> input) {
        int[] finished = finishOrder(new Adjacency(Input.vertexCount(input), Input.edges(input),
                false, false), true);
        if (finished == null) return Map.of("acyclic", false, "order", new int[0]);
        for (int left = 0, right = finished.length - 1; left < right; left++, right--) {
            int swap = finished[left]; finished[left] = finished[right]; finished[right] = swap;
        }
        return Map.of("acyclic", true, "order", finished);
    }

    static Map<String, Object> dag(Map<String, Object> input) {
        int n = Input.vertexCount(input), source = Input.source(input);
        int[][] edges = Input.edges(input);
        Adjacency graph = new Adjacency(n, edges, false, false);
        int[] finished = finishOrder(graph, true);
        if (finished == null) return Map.of("acyclic", false, "distance", new Long[0],
                "parent_edge", new int[0]);
        Long[] distance = new Long[n];
        int[] parentEdge = new int[n];
        Arrays.fill(parentEdge, -1); distance[source] = 0L;
        for (int i = n - 1; i >= 0; i--) {
            int vertex = finished[i];
            if (distance[vertex] == null) continue;
            for (int slot = graph.offset[vertex]; slot < graph.offset[vertex + 1]; slot++) {
                int to = graph.destination[slot], id = graph.edgeId[slot];
                long candidate = distance[vertex] + edges[id][2];
                if (distance[to] == null || candidate < distance[to]) {
                    distance[to] = candidate; parentEdge[to] = id;
                }
            }
        }
        return Map.of("acyclic", true, "distance", distance, "parent_edge", parentEdge);
    }

    /** Empty list means unreachable. Use arrays from an acyclic DAG result. */
    static List<Integer> reconstructRoute(int source, int target, Long[] distance,
                                          int[] parentEdge, int[][] edges) {
        if (distance[target] == null) return List.of();
        List<Integer> route = new ArrayList<>();
        int vertex = target;
        while (vertex != source) {
            if (route.size() >= distance.length) throw new IllegalArgumentException("Parent cycle");
            route.add(vertex);
            int id = parentEdge[vertex];
            if (id < 0 || id >= edges.length || edges[id][1] != vertex)
                throw new IllegalArgumentException("Invalid parent edge");
            int previous = edges[id][0];
            if (distance[previous] == null || distance[previous] + edges[id][2] != distance[vertex])
                throw new IllegalArgumentException("Parent does not witness the distance");
            vertex = previous;
        }
        route.add(source);
        Collections.reverse(route);
        return route;
    }
}
