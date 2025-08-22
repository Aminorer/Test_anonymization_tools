# Benchmark Results

Benchmark executed with `benchmark.py` on the provided dataset (`data/benchmark`).

| Run | Real time |
| --- | --- |
| Before changes | 2.023s |
| After caching/BK-tree | 2.043s |

Entity-level metrics remained identical after optimizations (excerpt from `benchmark_after.csv`):

```
entity,precision,recall,f1,support
DATE,1.0,1.0,1.0,100
EMAIL,1.0,1.0,1.0,100
PERSON,0.8571428571428571,1.0,0.9230769230769231,600
PHONE,1.0,1.0,1.0,100
```
