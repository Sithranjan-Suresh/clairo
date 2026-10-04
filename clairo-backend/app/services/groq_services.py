import logging
import os
import time

from groq import Groq
from dotenv import load_dotenv

from app.observability import LLM_CALLS, LLM_LATENCY

load_dotenv()

logger = logging.getLogger(__name__)

_raw_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Groq periodically deprecates/retires models (llama-3.3-70b-versatile was
# retired to Enterprise-only access on 2026-08-16, breaking every AI
# feature in this app until it was caught). Keep the model ID in exactly
# one place, overridable via GROQ_CHAT_MODEL without a code change.
CHAT_MODEL = os.getenv("GROQ_CHAT_MODEL", "openai/gpt-oss-120b")


class _InstrumentedCompletions:
    def __init__(self, inner):
        self._inner = inner

    def create(self, *args, task: str = "chat", **kwargs):
        start = time.perf_counter()
        try:
            result = self._inner.create(*args, **kwargs)
        except Exception:
            LLM_CALLS.labels(task, "error").inc()
            raise
        finally:
            LLM_LATENCY.labels(task).observe(time.perf_counter() - start)
        LLM_CALLS.labels(task, "ok").inc()
        return result


class _InstrumentedChat:
    def __init__(self, inner):
        self.completions = _InstrumentedCompletions(inner.completions)


class _InstrumentedClient:
    """Thin proxy over the Groq SDK that records latency/outcome metrics per
    task. Services pass an optional `task=` label to chat.completions.create."""

    def __init__(self, inner):
        self._inner = inner
        self.chat = _InstrumentedChat(inner.chat)

    def __getattr__(self, name):   # audio, models, ... pass straight through
        return getattr(self._inner, name)


client = _InstrumentedClient(_raw_client)
