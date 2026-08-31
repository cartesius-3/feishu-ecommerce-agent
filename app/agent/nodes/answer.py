"""通用节点：LLM 把结果格式化为自然语言回答。"""

from typing import Any, Dict

from app.agent.state import AgentState
from app.core.llm import get_llm
from app.prompts import ANSWER_PROMPT

import json


def answer_node(state: AgentState) -> Dict[str, Any]:
    prompt = ANSWER_PROMPT.format(
        query=state.get("user_input", ""),
        generated_sql=state.get("generated_sql", ""),
        query_result=json.dumps(state.get("query_result", []), ensure_ascii=False),
    )
    answer = get_llm().complete(prompt)
    return {"answer": answer}
