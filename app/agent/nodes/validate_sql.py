"""NL2SQL 节点：EXPLAIN 校验（真实连库但不取数）。

数据库引擎自己回答"这表有没有、这列叫不叫这个名"——
表不存在回 `Table 'xxx' doesn't exist`、列名错回 `Unknown column`，
这些报错信息就是 sql_error，喂回 LLM 走 correct_sql。
"""

from typing import Any, Dict

from app.agent.state import AgentState
from app.core.safety import enforce_read_only
from app.repositories.mysql.dw_repository import get_dw_repository


def validate_sql(state: AgentState) -> Dict[str, Any]:
    sql = state.get("generated_sql", "")
    if not sql:
        return {"sql_error": "NoSQLGenerated"}

    # 五层安全 2/3：正则黑名单 + SQLGlot AST（先于 EXPLAIN 拦截）
    safety_error = enforce_read_only(sql)
    if safety_error:
        return {"sql_error": safety_error}

    dw = get_dw_repository()
    error = dw.validate(sql)  # mock: SQLite EXPLAIN; mysql: 真实 EXPLAIN
    return {"sql_error": error}  # None=成功走 run_sql，否则走 correct_sql
