"""Independent small-graph oracles and reproducible full-limit checks."""
import copy
import gzip
import itertools
import json
import pathlib
import random
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from run import build, execute
OUT = ROOT / 'tests' / 'results'
OUT.mkdir(exist_ok=True)


def reachability(n, edges, undirected=False):
    reach = [[i == j for j in range(n)] for i in range(n)]
    for u, v, *rest in edges:
        reach[u][v] = True
        if undirected:
            reach[v][u] = True
    for k in range(n):
        for i in range(n):
            for j in range(n):
                reach[i][j] |= reach[i][k] and reach[k][j]
    return reach


def oracle(req):
    task, n = req['task'], req.get('n', 0)
    edges = req.get('edges', [])
    if task == 'ping':
        return {'status': 'ready'}
    if task == 'dsu':
        labels, states = list(range(n)), []
        for u, v in req['operations']:
            old, new = labels[v], labels[u]
            labels = [new if x == old else x for x in labels]
            states.append([len(set(labels)), max(labels.count(x) for x in labels)])
        return {'states': states}
    if task in ('kruskal', 'prim'):
        reach = reachability(n, edges, True)
        components = len({tuple(row) for row in reach})
        optimum = None
        # Exhaustive subsets: independent of both greedy implementations.
        for ids in itertools.combinations(range(len(edges)), n - components):
            chosen = [edges[i] for i in ids]
            if reachability(n, chosen, True) == reach:
                cost = sum(e[2] for e in chosen)
                optimum = cost if optimum is None else min(optimum, cost)
        return {'cost': optimum, 'components': components}
    reach = reachability(n, edges)
    if task == 'scc':
        return {'mutual': [[reach[u][v] and reach[v][u] for v in range(n)] for u in range(n)]}
    # A directed cycle exists iff an edge's destination reaches its source.
    acyclic = not any(reach[v][u] for u, v, *rest in edges)
    if task == 'topo' or not acyclic:
        return {'acyclic': acyclic}
    distance = [None] * n
    distance[req['source']] = 0
    # Bellman-Ford as an oracle; no topological traversal reused here.
    for _ in range(n - 1):
        for u, v, weight in edges:
            if distance[u] is not None and (distance[v] is None or distance[u] + weight < distance[v]):
                distance[v] = distance[u] + weight
    return {'acyclic': True, 'distance': distance}


def valid(req, answer, expected):
    try:
        task, n = req['task'], req.get('n', 0)
        edges = req.get('edges', [])
        if task in ('ping', 'dsu'):
            return answer == expected
        if task in ('kruskal', 'prim'):
            ids = answer['edge_ids']
            return (answer['cost'] == expected['cost'] and answer['components'] == expected['components']
                    and len(ids) == len(set(ids)) == n - expected['components']
                    and all(type(i) is int and 0 <= i < len(edges) for i in ids)
                    and sum(edges[i][2] for i in ids) == answer['cost']
                    and reachability(n, [edges[i] for i in ids], True) == reachability(n, edges, True))
        if task == 'scc':
            labels, condensation = answer['component'], answer['condensation']
            if len(labels) != n or any(type(x) is not int or x < 0 for x in labels):
                return False
            if any((labels[u] == labels[v]) != expected['mutual'][u][v] for u in range(n) for v in range(n)):
                return False
            pairs = {(labels[u], labels[v]) for u, v in edges if labels[u] != labels[v]}
            return len(condensation) == len(pairs) and set(map(tuple, condensation)) == pairs
        if answer['acyclic'] is not expected['acyclic']:
            return False
        if not expected['acyclic']:
            return answer.get('order') == [] if task == 'topo' else answer['distance'] == answer['parent_edge'] == []
        if task == 'topo':
            order = answer['order']
            if sorted(order) != list(range(n)):
                return False
            position = {v: i for i, v in enumerate(order)}
            return all(position[u] < position[v] for u, v in edges)
        distance, parents = answer['distance'], answer['parent_edge']
        if distance != expected['distance'] or len(parents) != n:
            return False
        source = req['source']
        for target in range(n):
            if target == source or distance[target] is None:
                if parents[target] != -1:
                    return False
                continue
            seen, vertex, total = set(), target, 0
            while vertex != source:
                if vertex in seen:
                    return False
                seen.add(vertex)
                edge_id = parents[vertex]
                if type(edge_id) is not int or not 0 <= edge_id < len(edges):
                    return False
                u, v, weight = edges[edge_id]
                if v != vertex:
                    return False
                vertex, total = u, total + weight
            if total != distance[target]:
                return False
        return True
    except (KeyError, IndexError, TypeError, ValueError):
        return False


def write_lines(path, rows):
    with path.open('w', encoding='utf-8', newline='\n') as stream:
        for row in rows:
            stream.write(json.dumps(row, separators=(',', ':')) + '\n')


def small_cases():
    cases = [{'task': 'ping'}]
    for task in ('dsu', 'kruskal', 'prim', 'scc', 'topo'):
        cases.append({'task': task, 'n': 0, 'operations' if task == 'dsu' else 'edges': []})
    cases += [
        {'task': 'dsu', 'n': 5, 'operations': [[0, 0], [0, 1], [1, 0], [2, 3], [1, 3]]},
        {'task': 'dag', 'n': 1, 'source': 0, 'edges': []},
        {'task': 'dag', 'n': 4, 'source': 0, 'edges': [[0, 1, -1], [2, 3, 1], [3, 2, 1]]},
        {'task': 'dag', 'n': 4, 'source': 0, 'edges': [[0, 1, -1], [0, 1, -1], [1, 2, 2]]},
        {'task': 'dag', 'n': 4, 'source': 0, 'edges': [[0, 1, 10**9], [1, 2, 10**9], [2, 3, 10**9]]},
        {'task': 'topo', 'n': 4, 'edges': [[0, 1], [0, 2], [1, 3], [2, 3]]},
        {'task': 'scc', 'n': 5, 'edges': [[0, 1], [1, 0], [1, 2], [1, 2], [2, 2], [2, 3]]},
    ]
    for task in ('kruskal', 'prim'):
        for edges, n in [([], 5), ([[0, 0, -9], [0, 1, -4], [0, 1, 2], [2, 3, 7]], 5),
                         ([[0, 1, 10**9], [1, 2, 10**9], [2, 3, 10**9]], 4),
                         ([[0, 1, 1], [1, 2, 1], [0, 2, 1]], 3)]:
            cases.append({'task': task, 'n': n, 'edges': edges})
    rng = random.Random(31019)
    for _ in range(60):
        n = rng.randrange(1, 7)
        edges = [[rng.randrange(n), rng.randrange(n), rng.randrange(-9, 10)] for _ in range(rng.randrange(10))]
        for task in ('kruskal', 'prim', 'scc', 'topo', 'dag', 'dsu'):
            req = {'task': task, 'n': n}
            if task == 'dsu':
                req['operations'] = [e[:2] for e in edges]
            else:
                req['edges'] = [e[:2] for e in edges] if task in ('scc', 'topo') else edges
            if task == 'dag':
                req['source'] = rng.randrange(n)
            cases.append(req)
        # Extra random DAGs exercise distances more often than arbitrary digraphs.
        cases.append({'task': 'dag', 'n': n, 'source': rng.randrange(n),
                      'edges': [e for e in edges if e[0] < e[1]]})
    return cases


def witness_checks():
    reports = []
    examples = [
        ({'task': 'kruskal', 'n': 3, 'edges': [[0, 1, 1], [1, 2, 1], [0, 2, 1]]},
         {'cost': 2, 'components': 1, 'edge_ids': [0, 1]},
         {'cost': 2, 'components': 1, 'edge_ids': [1, 2]},
         {'cost': 2, 'components': 1, 'edge_ids': [0, 0]}),
        ({'task': 'scc', 'n': 3, 'edges': [[0, 1], [1, 0], [1, 2]]},
         {'component': [0, 0, 1], 'condensation': [[0, 1]]},
         {'component': [7, 7, 9], 'condensation': [[7, 9]]},
         {'component': [0, 0, 1], 'condensation': []}),
        ({'task': 'topo', 'n': 3, 'edges': [[0, 2], [1, 2]]},
         {'acyclic': True, 'order': [0, 1, 2]}, {'acyclic': True, 'order': [1, 0, 2]},
         {'acyclic': True, 'order': [2, 0, 1]}),
        ({'task': 'dag', 'n': 2, 'source': 0, 'edges': [[0, 1, -1], [0, 1, -1]]},
         {'acyclic': True, 'distance': [0, -1], 'parent_edge': [-1, 0]},
         {'acyclic': True, 'distance': [0, -1], 'parent_edge': [-1, 1]},
         {'acyclic': True, 'distance': [0, -1], 'parent_edge': [-1, -1]})]
    for req, first, alternative, invalid in examples:
        expected = oracle(req)
        assert valid(req, first, expected) and valid(req, alternative, expected)
        assert not valid(req, invalid, expected)
        reports.append({'input': req, 'accepted': [first, alternative], 'rejected': invalid})
    write_lines(OUT / 'witness_checks.jsonl', reports)
    print('PASS alternative valid answers and invalid witnesses: forest, SCC, topo, DAG')


def scale_cases(command):
    n, m = 100000, 250000
    chain = [[v, v + 1] for v in range(n - 1)]
    repeated = chain + [chain[i % (n - 1)] for i in range(m - len(chain))]
    requests = [
        {'task': 'dsu', 'n': n, 'operations': repeated},
        *[{'task': task, 'n': n, 'edges': [[u, v, -10**9] for u, v in repeated]} for task in ('kruskal', 'prim')],
        {'task': 'scc', 'n': n, 'edges': repeated},
        {'task': 'topo', 'n': n, 'edges': repeated},
        {'task': 'dag', 'n': n, 'source': 0, 'edges': [[u, v, -10**9] for u, v in repeated]},
        {'task': 'scc', 'n': n, 'edges': chain + [[n - 1, 0]]},
        {'task': 'dag', 'n': n, 'source': 0, 'edges': [[v, v + 1, 1] for v in range(1, n - 1)] + [[n - 1, 1, 1]]},
    ]
    summaries = []
    with gzip.open(OUT / 'scale_inputs.jsonl.gz', 'wt', encoding='utf-8') as inputs, gzip.open(OUT / 'scale_actual.jsonl.gz', 'wt', encoding='utf-8') as outputs:
        for index, req in enumerate(requests):
            inputs.write(json.dumps(req, separators=(',', ':')) + '\n')
            answer = execute(command, [req])[0]
            outputs.write(json.dumps(answer, separators=(',', ':')) + '\n')
            task = req['task']
            if task == 'dsu':
                assert answer['states'] == [[n-i-1, i+2] if i < n-1 else [1, n] for i in range(m)]
            elif task in ('kruskal', 'prim'):
                ids = answer['edge_ids']
                assert answer['cost'] == -(n-1)*10**9 and answer['components'] == 1
                assert len(ids) == len(set(ids)) == n-1 and all(0 <= i < m for i in ids)
                assert {tuple(req['edges'][i][:2]) for i in ids} == set(map(tuple, chain))
            elif task == 'scc':
                labels = answer['component']
                assert len(labels) == n and all(type(x) is int and x >= 0 for x in labels)
                if index == 6:
                    assert len(set(labels)) == 1 and answer['condensation'] == []
                else:
                    pairs = {(labels[u], labels[v]) for u, v in chain}
                    assert len(set(labels)) == n and len(answer['condensation']) == n-1
                    assert set(map(tuple, answer['condensation'])) == pairs
            elif task == 'topo':
                assert answer['acyclic'] is True and answer['order'] == list(range(n))
            elif index == 7:
                assert answer == {'acyclic': False, 'distance': [], 'parent_edge': []}
            else:
                assert answer['acyclic'] is True and answer['distance'] == [-v*10**9 for v in range(n)]
                parents = answer['parent_edge']
                assert len(parents) == n and parents[0] == -1
                assert all(0 <= parents[v] < m and req['edges'][parents[v]] == [v-1, v, -10**9] for v in range(1,n))
            summaries.append({'case': index, 'task': task, 'n': n, 'rows': len(req.get('edges', req.get('operations', []))), 'passed': True})
    write_lines(OUT / 'scale_summary.jsonl', summaries)
    print('PASS 8 scale cases: full limits, deep chain, giant SCC, unreachable cycle')


def main():
    command = build('Java')
    cases = small_cases()
    expected = [oracle(req) for req in cases]
    # Repeat heterogeneous requests in the SAME JVM.
    actual = execute(command, cases + cases)
    for i, (req, answer, want) in enumerate(zip(cases + cases, actual, expected + expected)):
        assert valid(req, answer, want), (i, req, answer, want)
    write_lines(ROOT / 'tests' / 'my_cases.jsonl', cases)
    write_lines(OUT / 'expected.jsonl', expected)
    write_lines(OUT / 'actual.jsonl', actual)
    print(f'PASS {len(cases)} independently checked cases, repeated twice: {len(actual)} results')
    witness_checks()
    scale_cases(command)


if __name__ == '__main__':
    main()
