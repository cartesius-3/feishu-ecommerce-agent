"""NL2SQL 节点：ES 取值召回（精确匹配维度值）。"""

from typing import Any, Dict

from app.agent.state import AgentState
from app.repositories.es.fulltext_store import recall_values


def recall_value(state: AgentState) -> Dict[str, Any]:
    hits = []
    for kw in state.get("keywords", []):
        hits.extend(recall_values(kw, top_k=5))
    seen, out = set(), []
    for it in hits:
        key = (it.get("value"), it.get("field", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return {"retrieved_values": out}
