"""NL2SQL 节点：Milvus 指标召回（语义匹配指标定义/公式）。"""

from typing import Any, Dict

from app.agent.state import AgentState
from app.repositories.milvus.vector_store import recall_metrics


def recall_metric(state: AgentState) -> Dict[str, Any]:
    hits = []
    for kw in state.get("keywords", []):
        hits.extend(recall_metrics(kw, top_k=5))
    seen, out = set(), []
    for it in hits:
        key = (it.get("column") or it.get("name"), it.get("table", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return {"retrieved_metrics": out}
