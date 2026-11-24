# Bounded-memory file snapshot — local experiment

Baseline: core.py at b535850af64a460f96edfbcf56fa40df0d5ff974, Git blob f259b111ff5a2fd5a6102451c3adefd6058a8b54. New implementation streams 256 KiB chunks rather than calling Path.read_bytes() on the entire observed file. Hash and size match the baseline; no change to receipt schema or verdict semantics. This optimizes the observation path only; expected bytes supplied by the caller may still reside in memory, and trusted workspace / TOCTOU limitations remain.

Local Python 3.13.5, 64 MiB file, generated with 64 writes of 1 MiB each. Five alternating baseline/new trials on the same fixture; perf_counter_ns and tracemalloc around each snapshot. Baseline imported from saved pre-change core.py, new snapshot imported normally. All hashes and sizes matched. Median elapsed: baseline 80.466 ms, streaming 51.102 ms. Median peak traced Python allocations: baseline 67,113,773 bytes, streaming 529,561 bytes. Raw (ms, bytes) samples:

- baseline: (230.558705,67113862), (69.027171,67113773), (80.465864,67113773), (72.180068,67113773), (90.824854,67113773)
- streaming: (46.100698,529561), (51.1022,529561), (52.653515,529561), (54.059563,529561), (49.831716,529561)

These are local before/after measurements, not RSS, production latency or external comparator results. Cache and scheduling effects may influence elapsed times. No performance superiority over another project claimed.

Reproduce from repository root (requires baseline commit in git history):

```sh
git show b535850af64a460f96edfbcf56fa40df0d5ff974:src/openactionproof/core.py > /tmp/oap-core-apex-baseline.py
PYTHONPATH=src python - <<'PY'
import importlib.util,sys,tempfile,tracemalloc,time,statistics,pathlib
from openactionproof.core import snapshot
spec=importlib.util.spec_from_file_location('baseline_core','/tmp/oap-core-apex-baseline.py')
base=importlib.util.module_from_spec(spec);sys.modules[spec.name]=base;spec.loader.exec_module(base)
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d); file=p/'test.bin'; chunk=b'x'*(1024*1024)
 with file.open('wb') as f:
  for i in range(64):f.write(chunk)
 data={k:[] for k in ('baseline','streaming')}
 for i in range(5):
  for name,func in ([('baseline',base.snapshot),('streaming',snapshot)] if i%2==0 else [('streaming',snapshot),('baseline',base.snapshot)]):
   tracemalloc.start();start=time.perf_counter_ns();out=func(p,'test.bin');elapsed=(time.perf_counter_ns()-start)/1e6;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop();data[name].append((elapsed,peak));assert out['size']==64*1024*1024
  assert base.snapshot(p,'test.bin')==snapshot(p,'test.bin')
 for name,rows in data.items(): print(name,'median ms',statistics.median(x[0] for x in rows),'median traced peak bytes',statistics.median(x[1] for x in rows),'raw',rows)
PY
```

Regression test covers empty, single-byte, below/at/above chunk boundary, and multi-chunk content; asserts no Path.read_bytes call. Full local suite: 125/125 passed in 26.957 seconds using PYTHONPATH=src python -W error::ResourceWarning -m unittest discover -s tests -q. Both changed source/test blob hashes match locally tested bytes. Remote CI pending.
