"""NL2SQL 节点：三路合并（代码节点，非 LLM）。

合并过滤四步：
1. 去重（按 column 合并三路召回）
2. 补全指标依赖字段
3. 回填示例值到字段
4. 补全主外键（JOIN 条件）

前三步是确定性查表（从元数据知识库直查），第四步才是 LLM 过滤。
"""

from typing import Any, Dict, List

from app.agent.state import AgentState
from app.repositories.mysql.dw_repository import MOCK_META_FOREIGN_KEYS


def merge_retrieved_info(state: AgentState) -> Dict[str, Any]:
    columns = state.get("retrieved_columns", [])
    metrics = state.get("retrieved_metrics", [])
    values = state.get("retrieved_values", [])

    # 1. 按字段合并去重
    merged: Dict[str, Dict[str, Any]] = {}
    for col in columns:
        key = col.get("column") or col.get("name")
        if key:
            merged[key] = dict(col)

    # 2. 指标补充到对应字段（公式/定义挂到列上）
    for m in metrics:
        col_key = m.get("column")
        if col_key and col_key in merged:
            merged[col_key].setdefault("formula", m.get("formula"))
            merged[col_key].setdefault("metric", m.get("metric"))

    # 3. 回填示例值（ES 取到的具体值挂到字段）
    for v in values:
        field = v.get("field", "")
        col_key = field.split(".")[-1] if "." in field else field
        for item in merged.values():
            col_name = (item.get("column") or item.get("name") or "").split(".")[-1]
            if col_name == col_key:
                item.setdefault("value_example", v.get("value"))

    # 4. 补全主外键：按召回到的表，附上 JOIN 条件
    tables = {c.split(".")[0] for c in merged}
    fks = [fk for fk in MOCK_META_FOREIGN_KEYS if fk["table"] in tables]

    return {"merged_schema": {"tables": list(merged.values()), "foreign_keys": fks}}
