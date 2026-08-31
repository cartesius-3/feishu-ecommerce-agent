"""NL2SQL 节点：Milvus 字段召回（语义匹配列名/中文含义）。"""

from typing import Any, Dict

from app.agent.state import AgentState
from app.repositories.milvus.vector_store import recall_columns


def recall_column(state: AgentState) -> Dict[str, Any]:
    hits = []
    for kw in state.get("keywords", []):
        hits.extend(recall_columns(kw, top_k=5))
    seen, out = set(), []
    for it in hits:
        key = (it.get("column") or it.get("name"), it.get("table", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return {"retrieved_columns": out}
