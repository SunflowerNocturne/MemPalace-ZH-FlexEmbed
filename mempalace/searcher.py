#!/usr/bin/env python3
"""
searcher.py — Find anything. Exact words.

Semantic search against the palace.
Returns verbatim text — the actual words, never summaries.
"""

import logging
import re
from pathlib import Path

from .palace import get_collection

logger = logging.getLogger("mempalace_mcp")


class SearchError(Exception):
    """Raised when search cannot proceed (e.g. no palace found)."""


_QUERY_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]+|[A-Za-z0-9_]+")


def _extract_query_tokens(query: str) -> list[str]:
    """Extract language-agnostic query tokens for lightweight lexical reranking."""
    if not query:
        return []

    tokens = []
    seen = set()
    for raw in _QUERY_TOKEN_RE.findall(query.lower()):
        token = raw.strip()
        if len(token) < 2:
            continue
        if token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def _lexical_rerank_score(query: str, tokens: list[str], doc: str, meta: dict, dist: float) -> tuple[float, list[str]]:
    """Blend semantic similarity with exact lexical cues.

    Embeddings remain the main recall path, but explicit query words such as
    Chinese entity names or mixed-language keywords should strongly influence
    final ordering.
    """
    similarity = max(0.0, 1 - dist)
    if not tokens:
        return similarity, []

    source_name = Path(meta.get("source_file", "?")).name.lower()
    haystack = " ".join(
        [
            doc.lower(),
            meta.get("wing", "").lower(),
            meta.get("room", "").lower(),
            source_name,
        ]
    )

    matched = [token for token in tokens if token in haystack]
    lexical_ratio = len(matched) / len(tokens)
    exact_phrase_bonus = 0.08 if query.lower() in haystack else 0.0
    zero_match_penalty = 0.12 if not matched else 0.0
    score = (similarity * 0.72) + (lexical_ratio * 0.32) + exact_phrase_bonus - zero_match_penalty
    return score, matched


def build_where_filter(wing: str = None, room: str = None) -> dict:
    """Build ChromaDB where filter for wing/room filtering."""
    if wing and room:
        return {"$and": [{"wing": wing}, {"room": room}]}
    elif wing:
        return {"wing": wing}
    elif room:
        return {"room": room}
    return {}


def search(query: str, palace_path: str, wing: str = None, room: str = None, n_results: int = 5):
    """
    Search the palace. Returns verbatim drawer content.
    Optionally filter by wing (project) or room (aspect).
    """
    try:
        col = get_collection(palace_path, create=False)
    except Exception:
        print(f"\n  No palace found at {palace_path}")
        print("  Run: mempalace init <dir> then mempalace mine <dir>")
        raise SearchError(f"No palace found at {palace_path}")

    where = build_where_filter(wing, room)

    try:
        kwargs = {
            "query_texts": [query],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = col.query(**kwargs)

    except Exception as e:
        print(f"\n  Search error: {e}")
        raise SearchError(f"Search error: {e}") from e

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]

    if not docs:
        print(f'\n  No results found for: "{query}"')
        return

    print(f"\n{'=' * 60}")
    print(f'  Results for: "{query}"')
    if wing:
        print(f"  Wing: {wing}")
    if room:
        print(f"  Room: {room}")
    print(f"{'=' * 60}\n")

    for i, (doc, meta, dist) in enumerate(zip(docs, metas, dists), 1):
        similarity = round(max(0.0, 1 - dist), 3)
        source = Path(meta.get("source_file", "?")).name
        wing_name = meta.get("wing", "?")
        room_name = meta.get("room", "?")

        print(f"  [{i}] {wing_name} / {room_name}")
        print(f"      Source: {source}")
        print(f"      Match:  {similarity}")
        print()
        # Print the verbatim text, indented
        for line in doc.strip().split("\n"):
            print(f"      {line}")
        print()
        print(f"  {'─' * 56}")

    print()


def search_memories(
    query: str,
    palace_path: str,
    wing: str = None,
    room: str = None,
    n_results: int = 5,
    max_distance: float = 0.0,
) -> dict:
    """Programmatic search — returns a dict instead of printing.

    Used by the MCP server and other callers that need data.

    Args:
        query: Natural language search query.
        palace_path: Path to the ChromaDB palace directory.
        wing: Optional wing filter.
        room: Optional room filter.
        n_results: Max results to return.
        max_distance: Max cosine distance threshold. The palace collection uses
            cosine distance (hnsw:space=cosine) — 0 = identical, 2 = opposite.
            Results with distance > this value are filtered out. A value of
            0.0 disables filtering. Typical useful range: 0.3–1.0.
    """
    try:
        col = get_collection(palace_path, create=False)
    except Exception as e:
        logger.error("No palace found at %s: %s", palace_path, e)
        return {
            "error": "No palace found",
            "hint": "Run: mempalace init <dir> && mempalace mine <dir>",
        }

    where = build_where_filter(wing, room)

    fetch_count = min(max(n_results * 5, 20), 50)

    try:
        kwargs = {
            "query_texts": [query],
            "n_results": fetch_count,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = col.query(**kwargs)
    except Exception as e:
        return {"error": f"Search error: {e}"}

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]

    query_tokens = _extract_query_tokens(query)
    hits = []
    for doc, meta, dist in zip(docs, metas, dists):
        # Filter on raw distance before rounding to avoid precision loss
        if max_distance > 0.0 and dist > max_distance:
            continue
        rank_score, matched_tokens = _lexical_rerank_score(query, query_tokens, doc, meta, dist)
        hits.append(
            {
                "text": doc,
                "wing": meta.get("wing", "unknown"),
                "room": meta.get("room", "unknown"),
                "source_file": Path(meta.get("source_file", "?")).name,
                "similarity": round(max(0.0, 1 - dist), 3),
                "distance": round(dist, 4),
                "rank_score": round(rank_score, 4),
                "matched_terms": matched_tokens,
            }
        )

    hits.sort(key=lambda hit: (hit["rank_score"], hit["similarity"]), reverse=True)
    hits = hits[:n_results]

    return {
        "query": query,
        "filters": {"wing": wing, "room": room},
        "total_before_filter": len(docs),
        "results": hits,
    }
