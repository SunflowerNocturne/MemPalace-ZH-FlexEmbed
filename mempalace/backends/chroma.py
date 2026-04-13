"""ChromaDB-backed MemPalace collection adapter."""

import logging
import os
import sqlite3

import chromadb

from .base import BaseCollection
from .embeddings import ChromaDocumentEmbeddingFunction, get_embedding_runtime

logger = logging.getLogger(__name__)


def _fix_blob_seq_ids(palace_path: str):
    """Fix ChromaDB 0.6.x -> 1.5.x migration bug: BLOB seq_ids -> INTEGER.

    ChromaDB 0.6.x stored seq_id as big-endian 8-byte BLOBs. ChromaDB 1.5.x
    expects INTEGER. The auto-migration doesn't convert existing rows, causing
    the Rust compactor to crash with "mismatched types; Rust type u64 (as SQL
    type INTEGER) is not compatible with SQL type BLOB".

    Must run BEFORE PersistentClient is created (the compactor fires on init).
    """
    db_path = os.path.join(palace_path, "chroma.sqlite3")
    if not os.path.isfile(db_path):
        return
    try:
        with sqlite3.connect(db_path) as conn:
            for table in ("embeddings", "max_seq_id"):
                try:
                    rows = conn.execute(
                        f"SELECT rowid, seq_id FROM {table} WHERE typeof(seq_id) = 'blob'"
                    ).fetchall()
                except sqlite3.OperationalError:
                    continue
                if not rows:
                    continue
                updates = [(int.from_bytes(blob, byteorder="big"), rowid) for rowid, blob in rows]
                conn.executemany(f"UPDATE {table} SET seq_id = ? WHERE rowid = ?", updates)
                logger.info("Fixed %d BLOB seq_ids in %s", len(updates), table)
            conn.commit()
    except Exception:
        logger.exception("Could not fix BLOB seq_ids in %s", db_path)


class ChromaCollection(BaseCollection):
    """Thin adapter over a ChromaDB collection."""

    def __init__(self, collection, embedding_runtime=None):
        self._collection = collection
        self._embedding_runtime = embedding_runtime

    def add(self, *, documents, ids, metadatas=None):
        self._collection.add(documents=documents, ids=ids, metadatas=metadatas)

    def upsert(self, *, documents, ids, metadatas=None):
        self._collection.upsert(documents=documents, ids=ids, metadatas=metadatas)

    def query(self, **kwargs):
        if (
            self._embedding_runtime is not None
            and "query_texts" in kwargs
            and "query_embeddings" not in kwargs
        ):
            kwargs = dict(kwargs)
            query_texts = kwargs.pop("query_texts")
            kwargs["query_embeddings"] = self._embedding_runtime.embed_queries(list(query_texts))
        return self._collection.query(**kwargs)

    def get(self, **kwargs):
        return self._collection.get(**kwargs)

    def update(self, **kwargs):
        self._collection.update(**kwargs)

    def delete(self, **kwargs):
        self._collection.delete(**kwargs)

    def count(self):
        return self._collection.count()


class ChromaBackend:
    """Factory for MemPalace's default ChromaDB backend."""

    def get_collection(self, palace_path: str, collection_name: str, create: bool = False):
        if not create and not os.path.isdir(palace_path):
            raise FileNotFoundError(palace_path)

        if create:
            os.makedirs(palace_path, exist_ok=True)
            try:
                os.chmod(palace_path, 0o700)
            except (OSError, NotImplementedError):
                pass

        _fix_blob_seq_ids(palace_path)
        embedding_runtime = get_embedding_runtime()
        client = chromadb.PersistentClient(path=palace_path)
        kwargs = {}
        if embedding_runtime is not None:
            kwargs["embedding_function"] = ChromaDocumentEmbeddingFunction(embedding_runtime)
        if create:
            collection = client.get_or_create_collection(collection_name, **kwargs)
        else:
            collection = client.get_collection(collection_name, **kwargs)
        return ChromaCollection(collection, embedding_runtime=embedding_runtime)
