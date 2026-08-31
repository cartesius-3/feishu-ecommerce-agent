"""业务 Skill：内容生成（5 平台 × 模板库）。

检测平台 + 模板 → LLM 生成营销文案。文案生成走 content_skill，
与查数类（NL2SQL）分属不同子图——生成类不碰数据库。
"""

from typing import Any, Dict

from app.agent.state import AgentState
from app.core.llm import get_llm
from app.prompts import CONTENT_PROMPT

PLATFORMS = {"小红书": "种草风", "抖音": "带货风", "美团": "到店优惠风", "朋友圈": "私域风", "微博": "热点风"}


def content_skill(state: AgentState) -> Dict[str, Any]:
    text = state.get("user_input", "")
    platform = next((p for p in PLATFORMS if p in text), "小红书")
    template = PLATFORMS[platform]

    prompt = CONTENT_PROMPT.format(
        platform=platform, template=template,
        points=text if len(text) < 60 else text[:60] + "…",
    )
    return {"answer": get_llm().complete(prompt), "tool_result": {"platform": platform}}
