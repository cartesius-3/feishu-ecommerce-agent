"""业务 Skill：商品分析。

正则提取 SKU → 调 MCP 工具 get_sales_velocity() → LLM 生成分析报告。
"""

import re
from typing import Any, Dict

from app.agent.state import AgentState
from app.core.llm import get_llm
from app.mcp.tools.sales_tools import get_sales_velocity
from app.prompts import PRODUCT_ANALYSIS_PROMPT


def product_skill(state: AgentState) -> Dict[str, Any]:
    text = state.get("user_input", "")
    sku_match = re.search(r"SKU\d+", text, re.IGNORECASE)
    sku_id = sku_match.group(0) if sku_match else "SKU001"

    days_match = re.search(r"(\d+)\s*天", text)
    days = int(days_match.group(1)) if days_match else 7

    data = get_sales_velocity(sku_id, days=days)
    prompt = PRODUCT_ANALYSIS_PROMPT.format(
        sku_id=sku_id, days=days, data=json_dumps(data),
    )
    return {"answer": get_llm().complete(prompt), "tool_result": {"data": data}}


def json_dumps(obj) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False, indent=2)
