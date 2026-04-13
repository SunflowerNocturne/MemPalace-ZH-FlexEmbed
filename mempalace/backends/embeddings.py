"""Local embedding runtime support for MemPalace."""

from __future__ import annotations

import contextlib
import io
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..config import MempalaceConfig

DEFAULT_QUERY_INSTRUCTION = "Given a user query, retrieve relevant passages that answer the query"
logger = logging.getLogger(__name__)


def _build_sentence_transformer(model_name: str, device: str):
    """Instantiate sentence-transformers quietly.

    In MCP stdio mode, third-party progress output can confuse clients or be
    surfaced as opaque transport failures. We suppress stdout/stderr during
    model construction and surface real exceptions through Python exceptions.
    """
    from sentence_transformers import SentenceTransformer

    sink = io.StringIO()
    noisy_loggers = [
        logging.getLogger("sentence_transformers"),
        logging.getLogger("transformers"),
        logging.getLogger("transformers.modeling_utils"),
    ]
    previous_levels = [logger.level for logger in noisy_loggers]
    try:
        for noisy_logger in noisy_loggers:
            noisy_logger.setLevel(logging.ERROR)
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            return SentenceTransformer(
                model_name,
                device=device,
                processor_kwargs={"padding_side": "left"},
            )
    finally:
        for noisy_logger, level in zip(noisy_loggers, previous_levels):
            noisy_logger.setLevel(level)


def _normalize_device(device: Optional[str]) -> str:
    try:
        import torch

        if device:
            normalized = device.lower()
            if normalized == "mps":
                return "mps" if torch.backends.mps.is_available() else "cpu"
            if normalized == "cuda":
                return "cuda" if torch.cuda.is_available() else "cpu"
            return normalized

        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        if device:
            return device

    return "cpu"


@dataclass
class LocalEmbeddingRuntime:
    """Lazy-loaded sentence-transformers runtime."""

    model_name: str
    device: str
    batch_size: int = 4
    query_instruction: str = DEFAULT_QUERY_INSTRUCTION

    def __post_init__(self):
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "Local embeddings requested but sentence-transformers is not installed. "
                "Install the local embedding dependencies first."
            ) from exc

        try:
            self._model = _build_sentence_transformer(self.model_name, self.device)
        except RuntimeError as exc:
            if self.device == "mps" and "MPS backend is supported on MacOS 14.0+" in str(exc):
                logger.warning("Falling back to CPU embedding runtime because MPS is unavailable: %s", exc)
                self.device = "cpu"
                self._model = _build_sentence_transformer(self.model_name, self.device)
            else:
                raise
        return self._model

    def _encode(self, texts: List[str], *, prompt_name: Optional[str] = None, prompt: Optional[str] = None):
        if not texts:
            return []

        model = self._load_model()
        kwargs = {
            "batch_size": self.batch_size,
            "show_progress_bar": False,
            "normalize_embeddings": True,
            "convert_to_numpy": True,
        }
        if prompt is not None:
            kwargs["prompt"] = prompt
        elif prompt_name is not None:
            kwargs["prompt_name"] = prompt_name

        vectors = model.encode(texts, **kwargs)
        return vectors.tolist()

    def embed_documents(self, texts: List[str]):
        return self._encode(texts)

    def embed_queries(self, texts: List[str]):
        model = self._load_model()
        prompts = getattr(model, "prompts", {}) or {}
        if "query" in prompts:
            return self._encode(texts, prompt_name="query")

        prompt = f"Instruct: {self.query_instruction}\nQuery: "
        return self._encode(texts, prompt=prompt)


class ChromaDocumentEmbeddingFunction:
    """Chroma embedding function that embeds stored documents locally."""

    def __init__(self, runtime: LocalEmbeddingRuntime):
        self.runtime = runtime

    def __call__(self, input):
        return self.runtime.embed_documents(list(input))


_RUNTIME_CACHE: dict[Tuple[str, str, int, str], LocalEmbeddingRuntime] = {}


def get_embedding_runtime(config: Optional[MempalaceConfig] = None) -> Optional[LocalEmbeddingRuntime]:
    """Return a cached local embedding runtime, if configured."""
    cfg = config or MempalaceConfig()
    model_name = cfg.embedding_model_name
    if not model_name:
        return None

    device = _normalize_device(cfg.embedding_device)
    batch_size = max(1, cfg.embedding_batch_size)
    query_instruction = cfg.embedding_query_instruction
    key = (model_name, device, batch_size, query_instruction)
    if key not in _RUNTIME_CACHE:
        _RUNTIME_CACHE[key] = LocalEmbeddingRuntime(
            model_name=model_name,
            device=device,
            batch_size=batch_size,
            query_instruction=query_instruction,
        )
    return _RUNTIME_CACHE[key]
