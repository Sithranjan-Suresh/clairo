"""Measure what the retrieval cache buys on the real policy index.

    python scripts/benchmark_cache.py            # needs a built index (python run_ingest.py)

Runs the same set of (payer, CPT, denial reason) lookups twice: cold (cache
cleared, so every lookup embeds the query and scans the vector index) and warm
(every lookup is a cache hit). Uses whichever backend is configured
(REDIS_URL => Redis, otherwise the in-process cache).
"""
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GROQ_API_KEY", "benchmark")
os.environ.setdefault("LOG_LEVEL", "ERROR")

from app.cache import cache  # noqa: E402
from app.rag.embedder import get_embedding  # noqa: E402
from app.rag.retriever import retrieve_policy  # noqa: E402

PAYERS = ["UHC", "Aetna", "BCBS", "Cigna", "Humana"]
CPTS = ["29881", "27447", "93306", "70553", "43239", "22612"]
REASONS = ["medical necessity not established", "prior authorization missing"]
CLASSIFICATIONS = {"medical necessity not established": "medical_necessity",
                   "prior authorization missing": "prior_authorization"}


def workload():
    return [(p, c, r) for p in PAYERS for c in CPTS for r in REASONS]


def run_pass(queries):
    timings = []
    for payer, cpt, reason in queries:
        start = time.perf_counter()
        retrieve_policy(payer, "", 3, CLASSIFICATIONS[reason], cpt, reason)
        timings.append((time.perf_counter() - start) * 1000)
    return timings


def summarize(label, timings):
    ordered = sorted(timings)
    p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
    print(f"{label:<6} n={len(timings):<3} mean={statistics.mean(timings):8.2f} ms  "
          f"median={statistics.median(timings):8.2f} ms  p95={p95:8.2f} ms")
    return statistics.mean(timings), statistics.median(timings)


def main():
    queries = workload()
    print(f"cache backend: {cache.backend} | {len(queries)} distinct lookups")
    get_embedding("warm up the ONNX embedding model")   # exclude one-off model load from "cold"
    cache.clear()
    cold_mean, cold_median = summarize("cold", run_pass(queries))
    warm_mean, warm_median = summarize("warm", run_pass(queries))
    print(f"speedup: {cold_mean / warm_mean:,.0f}x on the mean, "
          f"{cold_median / warm_median:,.0f}x on the median "
          f"({100 * (1 - warm_mean / cold_mean):.2f}% less latency)")


if __name__ == "__main__":
    main()
