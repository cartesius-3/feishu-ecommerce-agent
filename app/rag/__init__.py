"""RAG 知识库（文档问答）。

知识类文档走 RAG：分块 → 向量化 → 检索 → 生成（带来源引用）。
与 NL2SQL 的分工：数据类问题（查数）走 12 节点管线；知识类问题走 RAG。

mock 模式：内存文档 + hash 向量（离线演示）；
真实模式：Chroma/Milvus 向量库 + TEI embedding。
"""

import hashlib
import re
from typing import Any, Dict, List

from app.core.embedder import get_embedder
from app.core.llm import get_llm

# 内置示例知识文档（演示用）
_DEMO_DOCS = [
    ("《美团点评运营》", "美团点评的曝光量提升：1) 完善店铺头图与团购套餐；"
     "2) 参加平台活动获取流量加权；3) 鼓励好评积累店铺分。"),
    ("《抖音本地生活》", "抖音本地生活：用短视频+直播带货，挂载团购链接，"
     "配合本地推投流，按 ROI 调整预算。"),
    ("《小红书种草》", "小红书种草：图文笔记强调真实体验与场景，"
     "标题带关键词，正文加话题标签提升搜索曝光。"),
]


class Chunker:
    """按段落/固定长度分块。"""

    def chunk(self, text: str, size: int = 256, overlap: int = 32) -> List[str]:
        paras = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
        chunks = []
        for p in paras:
            if len(p) <= size:
                chunks.append(p)
            else:
                step = size - overlap
                chunks.extend(p[i:i + size] for i in range(0, len(p), step))
        return chunks


class MemoryRagStore:
    """内存向量库（mock）：哈希向量 + 余弦相似度。"""

    def __init__(self) -> None:
        self._embedder = get_embedder()
        self._chunks: List[Dict[str, Any]] = []

    def add_documents(self, docs: List[Dict[str, str]]) -> None:
        chunker = Chunker()
        for doc in docs:
            for text in chunker.chunk(doc["text"]):
                self._chunks.append({
                    "source": doc.get("source", ""),
                    "text": text,
                    "vector": self._embedder.embed_query(text),
                })

    def search(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        qv = self._embedder.embed_query(query)
        scored = []
        for c in self._chunks:
            sim = sum(a * b for a, b in zip(qv, c["vector"]))
            scored.append((sim, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"source": c["source"], "text": c["text"], "score": round(s, 4)}
                for s, c in scored[:top_k]]


_rag_store: MemoryRagStore = None


def _get_store() -> MemoryRagStore:
    global _rag_store
    if _rag_store is None:
        _rag_store = MemoryRagStore()
        _rag_store.add_documents(
            [{"source": s, "text": t} for s, t in _DEMO_DOCS]
        )
    return _rag_store


def rag_answer(query: str, top_k: int = 4) -> Dict[str, Any]:
    """RAG 问答：检索 + 带引用的生成。"""
    hits = _get_store().search(query, top_k)
    context = "\n\n".join(f"[{h['source']}] {h['text']}" for h in hits)
    prompt = (
        "你是一个知识库问答助手。只基于以下检索内容回答，不要编造；"
        "若内容无关，明确说知识库没有相关信息。回答末尾列出引用来源。\n\n"
        f"检索内容：\n{context}\n\n问题：{query}\n\n回答："
    )
    answer = get_llm().complete(prompt)
    return {"answer": answer, "sources": [h["source"] for h in hits]}
