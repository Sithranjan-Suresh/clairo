import time

from app import cache as cache_module
from app.cache import Cache, cached


def test_memory_cache_roundtrip_and_miss():
    c = Cache()
    assert c.backend == "memory"
    assert c.get("ns", "k") is None
    c.set("ns", "k", {"a": [1, 2]}, ttl=60)
    assert c.get("ns", "k") == {"a": [1, 2]}
    assert c.get("other-ns", "k") is None            # namespaces are isolated


def test_cache_distinguishes_empty_results_from_misses():
    c = Cache()
    c.set("ns", "k", [], ttl=60)
    assert c.get("ns", "k") == []


def test_entries_expire(monkeypatch):
    c = Cache()
    c.set("ns", "k", "v", ttl=10)
    now = time.monotonic()
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: now + 11)
    assert c.get("ns", "k") is None


def test_memory_cache_is_bounded(monkeypatch):
    monkeypatch.setattr(cache_module, "_MAX_MEMORY_ITEMS", 5)
    c = Cache()
    for i in range(20):
        c.set("ns", str(i), i, ttl=60)
    assert len(c._memory._data) <= 5
    assert c.get("ns", "19") == 19                    # newest survive


def test_cached_decorator_memoizes_by_arguments():
    calls = []

    @cached("unit", ttl=60)
    def lookup(payer, cpt=""):
        calls.append((payer, cpt))
        return [payer, cpt]

    cache_module.cache.clear()
    assert lookup("UHC", cpt="29881") == ["UHC", "29881"]
    assert lookup("UHC", cpt="29881") == ["UHC", "29881"]
    assert len(calls) == 1                            # second call was a hit
    lookup("UHC", cpt="27447")
    assert len(calls) == 2                            # different args -> different key


def test_redis_outage_degrades_to_a_miss_instead_of_an_error():
    class DeadRedis:
        def get(self, key):
            raise ConnectionError("redis down")

        def set(self, key, value, ttl):
            raise ConnectionError("redis down")

        def clear(self):
            raise ConnectionError("redis down")

    c = Cache()
    c._redis = DeadRedis()
    assert c.backend == "redis"
    assert c.get("ns", "k") is None                   # no exception
    c.set("ns", "k", 1, ttl=60)                       # no exception
    c.clear()


def test_retrieval_is_served_from_cache_on_repeat():
    from unittest.mock import patch

    from app.rag import retriever

    cache_module.cache.clear()
    with patch.object(retriever, "_retrieve_policy", return_value=[{"text": "x"}]) as inner:
        first = retriever.retrieve_policy("UHC", "", 3, "medical_necessity", "29881", "denied")
        second = retriever.retrieve_policy("UHC", "", 3, "medical_necessity", "29881", "denied")
    assert first == second == [{"text": "x"}]
    assert inner.call_count == 1
