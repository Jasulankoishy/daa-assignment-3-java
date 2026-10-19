"""Run and capture real evidence; compilation is outside benchmark timers."""
import json
import pathlib
import platform
import subprocess
import sys
from datetime import datetime, timezone
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'tests' / 'results'
OUT.mkdir(exist_ok=True)

def capture(name, command):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=180)
    (OUT / name).write_text(result.stdout, encoding='utf-8')
    (OUT / (name + '.stderr.txt')).write_text(result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    print(f'PASS {name}')

capture('setup.txt', [sys.executable, 'tools/run.py', '--setup'])
capture('public.txt', [sys.executable, 'tools/run.py', '--check'])
capture('own.txt', [sys.executable, 'tests/check_own.py'])
subprocess.run(['javac', '--release', '17', '-encoding', 'UTF-8', '-cp', '.build/Java',
                '-d', '.build/Java', 'tests/Experiments.java'], cwd=ROOT, check=True)
capture('routes.jsonl', ['java', '-Xmx384m', '-cp', '.build/Java', 'Experiments'])
capture('benchmark.jsonl', ['java', '-Xmx384m', '-cp', '.build/Java', 'Experiments', 'benchmark'])
java = subprocess.run(['java', '-version'], capture_output=True, text=True)
environment = {'recorded_utc': datetime.now(timezone.utc).isoformat(), 'os': platform.platform(),
               'cpu': platform.processor(), 'python': sys.version, 'java': java.stderr.strip(),
               'java_heap': '-Xmx384m', 'compile_target': '--release 17', 'timer': 'System.nanoTime()',
               'boundary': 'Complete Algorithms.kruskal/prim invocation: input row conversion, algorithm data structures and result construction included; graph generation, JSON parsing, JVM startup, compilation, validation and printing excluded.',
               'warmup': '5 calls per method per size after an untimed validation call',
               'trials': '5 per method per size; first method alternates by trial',
               'generator': 'tests/Experiments.java graph(): java.util.Random(31019+n); negative chain, nonnegative random extra edges',
               'limitations': 'One JVM per benchmark run, shared desktop load, JIT and GC noise; structured graphs with a known optimum, not a survey of arbitrary graph families.'}
if sys.platform == 'win32':
    from hardware_info import hardware_info
    environment['hardware'] = hardware_info()
(OUT / 'environment.json').write_text(json.dumps(environment, indent=2), encoding='utf-8')
print('Evidence saved in tests/results/')
