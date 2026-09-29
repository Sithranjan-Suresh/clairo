from chromadb.utils import embedding_functions

# Uses ChromaDB's bundled ONNX build of all-MiniLM-L6-v2 (same model, same
# 384-dim vectors as the sentence-transformers version this replaced)
# instead of loading it through PyTorch. sentence-transformers pulls in
# full PyTorch, which alone typically holds 300-500MB resident just from
# being imported — on a 512MB-RAM deployment (e.g. Render's free tier)
# that's enough on its own to get the process OOM-killed once FastAPI,
# SQLAlchemy, and chromadb's own baseline are added on top. onnxruntime
# has no such overhead.
_embedding_function = None


def get_embedding_function():
    global _embedding_function
    if _embedding_function is None:
        _embedding_function = embedding_functions.DefaultEmbeddingFunction()
    return _embedding_function


def get_embedding(text: str):
    # .tolist() keeps the return type a plain list, matching what callers
    # got from the old sentence-transformers implementation (numpy arrays
    # don't JSON-serialize cleanly if this value ever ends up in a response).
    return get_embedding_function()([text])[0].tolist()
