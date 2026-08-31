"""NL2SQL 节点：执行 SQL（EXPLAIN 通过后只读查询一次）。"""

from typing import Any, Dict, List

from app.agent.state import AgentState
from app.repositories.mysql.dw_repository import get_dw_repository


def run_sql(state: AgentState) -> Dict[str, Any]:
    sql = state.get("generated_sql", "")
    dw = get_dw_repository()
    result: List[Dict[str, Any]] = dw.query(sql)
    return {"query_result": result}
