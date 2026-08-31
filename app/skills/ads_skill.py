"""业务 Skill：广告分析。

提取广告维度 → 调 MCP 工具 → 计算 ROI/ROAS（口径：销售额÷广告费）→ LLM 报告。
"""

from typing import Any, Dict

from app.agent.state import AgentState
from app.core.llm import get_llm
from app.mcp.tools.sales_tools import get_ads_performance
from app.prompts import ADS_ANALYSIS_PROMPT

import json


def ads_skill(state: AgentState) -> Dict[str, Any]:
    text = state.get("user_input", "")
    channel = next((c for c in ("搜索", "信息流", "短视频", "直播") if c in text), "全部")

    data = get_ads_performance(channel=channel)
    prompt = ADS_ANALYSIS_PROMPT.format(data=json.dumps(data, ensure_ascii=False))
    return {"answer": get_llm().complete(prompt), "tool_result": {"data": data}}
