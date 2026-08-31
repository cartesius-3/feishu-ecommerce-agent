"""Milvus 向量检索（字段 + 指标召回）。

- 真实模式：pymilvus 连接 Milvus，向量检索 schema 语义。
- mock 模式：基于元数据知识库的内存过滤（关键词命中），离线演示。

检索对象两类（与技术文档三路召回对应）：
  recall_column —— 字段级：列名/中文名/语义
  recall_metric —— 指标级：指标定义/公式
"""

from typing import Any, Dict, List

from app.config import settings
from app.core.embedder import get_embedder
from app.repositories.mysql.dw_repository import MOCK_META_COLUMNS


class MockVectorStore:
    """内存向量库：用关键词包含匹配模拟语义召回。"""

    name = "mock"

    def __init__(self, docs: List[Dict[str, Any]]) -> None:
        self._docs = docs

    def search(self, keyword: str, top_k: int = 5) -> List[Dict[str, Any]]:
        scored = []
        for doc in self._docs:
            haystack = " ".join(str(v) for v in doc.values())
            if keyword in haystack:
                scored.append((1.0, doc))
            elif any(k in haystack for k in _split_keyword(keyword)):
                scored.append((0.6, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [dict(d, score=s) for s, d in scored[:top_k]]


class MilvusVectorStore:
    """Milvus 真实实现（pymilvus）。未安装/未连接时抛错提示切 mock。"""

    name = "milvus"

    def __init__(self, collection: str) -> None:
        try:
            from pymilvus import Collection, connections
        except ImportError:
            raise RuntimeError("需要安装 pymilvus；离线演示请设 EMBED_MODE=mock")
        connections.connect(alias="default", uri=settings.milvus_uri)
        self._collection = Collection(collection)

    def search(self, keyword: str, top_k: int = 5) -> List[Dict[str, Any]]:
        from pymilvus import utility

        vec = get_embedder().embed_query(keyword)
        hits = self._collection.search(
            data=[vec], anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"nprobe": 16}},
            limit=top_k, output_fields=["name", "table", "example", "formula"],
        )
        results = []
        for h in hits[0]:
            results.append({
                "name": h.entity.get("name"),
                "table": h.entity.get("table"),
                "example": h.entity.get("example"),
                "formula": h.entity.get("formula"),
                "score": h.score,
            })
        return results


def _split_keyword(keyword: str) -> List[str]:
    """粗分关键词（mock 召回辅助）。"""
    return [k for k in keyword.replace(" ", "").split() if len(k) > 1]


# 字段与指标两个集合的 mock 实例（进程级单例）
_column_store = MockVectorStore(MOCK_META_COLUMNS)
_metric_store = MockVectorStore(
    [c for c in MOCK_META_COLUMNS if c.get("metric") is not None]
)


def recall_columns(keyword: str, top_k: int = 5) -> List[Dict[str, Any]]:
    if settings.embed_mode == "mock":
        return _column_store.search(keyword, top_k)
    store = MilvusVectorStore("meta_columns")
    return store.search(keyword, top_k)


def recall_metrics(keyword: str, top_k: int = 5) -> List[Dict[str, Any]]:
    if settings.embed_mode == "mock":
        return _metric_store.search(keyword, top_k)
    store = MilvusVectorStore("meta_metrics")
    return store.search(keyword, top_k)
