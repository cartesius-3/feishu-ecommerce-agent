"""NL2SQL 节点：LLM 修正 SQL（把 EXPLAIN 报错喂回 LLM）。"""

from typing import Any, Dict

from app.agent.state import AgentState
from app.core.llm import get_llm
from app.prompts import CORRECT_SQL_PROMPT


def correct_sql(state: AgentState) -> Dict[str, Any]:
    prompt = CORRECT_SQL_PROMPT.format(
        generated_sql=state.get("generated_sql", ""),
        sql_error=state.get("sql_error", ""),
        tables_yaml="(同 generate_sql 上下文)",
        metrics_yaml="(见 tables 注释)",
        query=state.get("user_input", ""),
    )
    sql = get_llm().complete(prompt, temperature=0).strip()
    if sql.startswith("```"):
        sql = sql.split("```")[1]
        if sql.startswith("sql"):
            sql = sql[3:]
    return {"generated_sql": sql.strip(), "sql_error": None}
