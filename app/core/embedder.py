"""Embedding 统一层。

- embed_mode=mock：基于字符串 hash 的确定性向量（同串同向量），仅供离线演示。
- embed_mode=tei：远程 TEI 服务（BGE-large-zh-v1.5）。
- embed_mode=local：本地 sentence-transformers MiniLM。
"""

import hashlib
import math
from typing import List

from app.config import settings


def _hash_vector(text: str, dim: int = 1024) -> List[float]:
    """把文本确定性映射到 dim 维向量（词袋式 hash）。"""
    vec = [0.0] * dim
    for token in text.lower().split():
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest()[:8], 16)
        idx = h % dim
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class MockEmbedder:
    name = "mock"

    def embed_query(self, text: str) -> List[float]:
        return _hash_vector(text, settings.embedding_dim)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_query(t) for t in texts]


class TeiEmbedder:
    """TEI（Text Embeddings Inference）服务。"""

    name = "tei"

    def _embed(self, text: str) -> List[float]:
        import requests

        resp = requests.post(
            f"{settings.tei_base_url}/embed",
            json={"inputs": text},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(t) for t in texts]


class LocalEmbedder:
    """本地 sentence-transformers。"""

    name = "local"

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(settings.local_embed_model)

    def embed_query(self, text: str) -> List[float]:
        return self._model.encode(text).tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._model.encode(texts).tolist()


def get_embedder():
    if settings.embed_mode == "tei":
        return TeiEmbedder()
    if settings.embed_mode == "local":
        return LocalEmbedder()
    return MockEmbedder()
