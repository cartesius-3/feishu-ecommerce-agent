"""业务 Skill：帮助引导。LLM + HELP_PROMPT 介绍能力。"""

from typing import Any, Dict

from app.agent.state import AgentState
from app.core.llm import get_llm
from app.prompts import HELP_PROMPT


def help_skill(state: AgentState) -> Dict[str, Any]:
    return {"answer": get_llm().complete(HELP_PROMPT)}
