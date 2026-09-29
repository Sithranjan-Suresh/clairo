import os
import tempfile

# Set before any `app.*` module is imported so services that read these at
# import time (Groq client, ChromaDB path) never touch real credentials or
# the repo's actual vector store during tests.
os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ.setdefault("CHROMA_PATH", os.path.join(tempfile.gettempdir(), "clairo_test_chroma"))
