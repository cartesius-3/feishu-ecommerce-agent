"""意图路由节点。

LLM + 语义判断（语义问题交给 LLM，不是规则表）→ 把 intent 写进 state，
之后由 LangGraph 条件边读 state 分发——判断在节点、选路在边。
"""

from typing import Any, Dict

from app.agent.state import AgentState
from app.core.llm import get_llm
from app.prompts import INTENT_ROUTER_PROMPT

VALID_INTENTS = {"data_query", "product", "ads", "content", "file", "help"}


def intent_router(state: AgentState) -> Dict[str, Any]:
    prompt = INTENT_ROUTER_PROMPT.format(user_input=state.get("user_input", ""))
    raw = get_llm().complete(prompt).strip().lower()
    intent = raw if raw in VALID_INTENTS else "help"
    return {"intent": intent}
