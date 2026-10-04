"""Keeps the payer_policies catalog table in step with the vector index."""
import logging
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PayerPolicy
from app.models.base import utcnow
from app.rag.retriever import clean_source_label
from app.rag.vectorstore import collection

logger = logging.getLogger(__name__)


def sync_catalog(db: Session) -> int:
    """Upsert one row per indexed policy PDF; drop rows whose PDF left the index."""
    data = collection.get(include=["metadatas"])
    chunk_counts: Counter = Counter()
    payers: dict = {}
    for meta in data.get("metadatas") or []:
        source = (meta or {}).get("source")
        if not source:
            continue
        chunk_counts[source] += 1
        payers.setdefault(source, meta.get("payer") or "Unknown")

    existing = {p.source_file: p for p in db.scalars(select(PayerPolicy)).all()}
    for source, count in chunk_counts.items():
        row = existing.pop(source, None)
        if row is None:
            row = PayerPolicy(source_file=source, payer=payers[source],
                              title=clean_source_label(source), chunk_count=count)
            db.add(row)
        else:
            row.payer, row.chunk_count, row.synced_at = payers[source], count, utcnow()
    for stale in existing.values():
        db.delete(stale)
    db.commit()
    logger.info("policy catalog synced: %d documents", len(chunk_counts))
    return len(chunk_counts)
