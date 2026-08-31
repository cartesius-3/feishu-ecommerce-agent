"""NL2SQL 节点：LLM 并行过滤表 + 指标。

把合并后的候选 schema 交给 LLM 过滤，压缩喂给 SQL 生成的上下文，
减少 token 消耗、砍掉幻觉空间。
"""

from typing import Any, Dict

from app.agent.state import AgentState
from app.core.llm import get_llm
from app.prompts import FILTER_SCHEMA_PROMPT

import yaml


def _to_yaml(merged: Dict[str, Any]) -> str:
    tables = {c.get("column", c.get("name")): {
        "table": c.get("table", ""),
        "name": c.get("name", ""),
        "example": c.get("example", ""),
        "formula": c.get("formula", ""),
    } for c in merged.get("tables", [])}
    metrics = {c.get("metric"): {
        "column": c.get("column", c.get("name")),
        "formula": c.get("formula", ""),
    } for c in merged.get("tables", []) if c.get("metric")}
    return (yaml.safe_dump({"tables": tables}, allow_unicode=True, sort_keys=False)
            + yaml.safe_dump({"metrics": metrics}, allow_unicode=True, sort_keys=False))


def filter_table_and_metric(state: AgentState) -> Dict[str, Any]:
    merged = state.get("merged_schema", {"tables": [], "foreign_keys": []})
    if not merged.get("tables"):
        return {"merged_schema": merged}

    prompt = FILTER_SCHEMA_PROMPT.format(
        tables_yaml=_to_yaml(merged),
        metrics_yaml="{}",
        query=state.get("user_input", ""),
    )
    raw = get_llm().complete(prompt)
    # mock 下 LLM 输出可能不是 YAML dict：解析失败时保守不过滤（保留全部候选）
    try:
        parsed = yaml.safe_load(raw)
        if not isinstance(parsed, dict):
            parsed = {}
        filtered_tables = parsed.get("filtered_tables") or merged["tables"]
    except yaml.YAMLError:
        filtered_tables = merged["tables"]

    merged["tables"] = filtered_tables if isinstance(filtered_tables, list) else merged["tables"]
    return {"merged_schema": merged}
