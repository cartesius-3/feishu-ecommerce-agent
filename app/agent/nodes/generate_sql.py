"""NL2SQL 节点：LLM 生成 SQL（temperature=0 保证确定性）。"""

from typing import Any, Dict

from app.agent.state import AgentState
from app.core.llm import get_llm
from app.prompts import GENERATE_SQL_PROMPT


def _schema_yaml(merged: Dict[str, Any]) -> str:
    lines = []
    for col in merged.get("tables", []):
        table = col.get("table", "?")
        col_key = col.get("column") or col.get("name", "?")
        meta = []
        if col.get("name"):
            meta.append(f"# {col['name']}")
        if col.get("formula"):
            meta.append(f"# 公式: {col['formula']}")
        if col.get("example") is not None:
            meta.append(f"# 示例: {col['example']}")
        lines.append(f"{col_key}: {', '.join(meta)}")
    return "\n".join(lines) or "- (no candidate)"


def generate_sql(state: AgentState) -> Dict[str, Any]:
    merged = state.get("merged_schema", {"tables": [], "foreign_keys": []})
    date_info = state.get("tool_result", {}).get("date_info", "today unknown")
    db_info = state.get("tool_result", {}).get("db_info", "dialect unknown")

    prompt = GENERATE_SQL_PROMPT.format(
        tables_yaml=_schema_yaml(merged),
        metrics_yaml="(见 tables 注释)",
        date_info=date_info,
        db_info=db_info,
        query=state.get("user_input", ""),
    )
    sql = get_llm().complete(prompt, temperature=0)
    sql = _strip_markdown(sql)
    return {"generated_sql": sql}


def _strip_markdown(sql: str) -> str:
    sql = sql.strip()
    if sql.startswith("```"):
        sql = sql.split("```")[1]
        if sql.startswith("sql"):
            sql = sql[3:]
    return sql.strip()
