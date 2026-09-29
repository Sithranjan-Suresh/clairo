from app.rag.ingest import split_text


def test_split_text_empty():
    assert split_text("") == []
    assert split_text("   \n\n  ") == []


def test_split_text_keeps_sentences_whole():
    text = "First sentence is short. " * 40  # well over chunk_size
    chunks = split_text(text, chunk_size=200, overlap=20)

    assert len(chunks) > 1
    for chunk in chunks:
        # Every chunk should end on a sentence boundary, not mid-word.
        assert chunk.strip().endswith(".")
        assert len(chunk) <= 200 + 20 + 1  # allow for the carried-over tail


def test_split_text_overlap_carries_context_across_chunks():
    sentence = "Prior authorization is required for this procedure. "
    text = (sentence * 30).strip()
    chunks = split_text(text, chunk_size=150, overlap=50)

    assert len(chunks) >= 2
    # The tail of one chunk should reappear at the start of the next,
    # so a criterion split across the boundary still appears intact somewhere.
    assert chunks[0][-20:].strip() in chunks[1]


def test_split_text_oversized_sentence_is_not_dropped():
    huge_sentence = "x" * 1000 + "."
    chunks = split_text(f"Short one. {huge_sentence}", chunk_size=100, overlap=10)

    assert any(huge_sentence in c for c in chunks)
