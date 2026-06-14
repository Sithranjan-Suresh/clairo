import os
from uuid import uuid4

from app.rag.loader import load_pdf_text
from app.rag.embedder import get_embedding
from app.rag.vectorstore import collection


def ingest_policy(payer: str, file_path: str):

    raw_text = load_pdf_text(file_path)

    # split into chunks (simple version)
    chunks = split_text(raw_text)

    for i, chunk in enumerate(chunks):

        embedding = get_embedding(chunk)

        collection.add(
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


def split_text(text: str, chunk_size: int = 800):
    return [
        text[i:i + chunk_size]
        for i in range(0, len(text), chunk_size)
    ]