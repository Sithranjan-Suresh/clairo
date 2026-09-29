import re
from uuid import uuid4

from app.rag.loader import load_pdf_text
from app.rag.embedder import get_embedding
from app.rag import vectorstore


def ingest_policy(payer: str, file_path: str):

    raw_text = load_pdf_text(file_path)

    chunks = split_text(raw_text)

    for i, chunk in enumerate(chunks):

        embedding = get_embedding(chunk)

        vectorstore.collection.add(
            ids=[str(uuid4())],
            embeddings=[embedding],
            documents=[chunk],
            metadatas=[
                {
                    "payer": payer,
                    "source": file_path,
                    "chunk_index": i
                }
            ]
        )


def split_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    """Paragraph/sentence-aware chunking with overlap.

    Splitting on a raw character count (the previous approach) routinely
    cuts policy criteria and clinical requirements mid-sentence, which
    hurts retrieval quality for the appeal-generation pipeline that grounds
    itself in these chunks. Instead we greedily pack whole sentences into
    chunks up to `chunk_size`, and carry the tail of each chunk into the
    next one (`overlap`) so criteria that span a chunk boundary still show
    up whole in at least one chunk.
    """
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    sentences = re.split(r"(?<=[.!?])\s+", text)

    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if not sentence:
            continue
        # A single sentence longer than chunk_size can't be packed further —
        # flush what we have and emit it on its own.
        if len(sentence) > chunk_size:
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.append(sentence.strip())
            continue

        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) > chunk_size and current:
            chunks.append(current.strip())
            # Carry the tail of the previous chunk forward for context overlap.
            tail = current[-overlap:].strip()
            current = f"{tail} {sentence}".strip() if tail else sentence
        else:
            current = candidate

    if current:
        chunks.append(current.strip())

    return chunks
