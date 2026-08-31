"""业务 Skill：文件分析。

文件已在 load_file 节点解析成结构化摘要（列统计 + 样本），
这里由 LLM 生成分析报告——数字来自解析器，LLM 只配词不配数。
"""

from typing import Any, Dict

from app.agent.state import AgentState
from app.core.llm import get_llm
from app.prompts import FILE_ANALYSIS_PROMPT


def file_analysis_skill(state: AgentState) -> Dict[str, Any]:
    prompt = FILE_ANALYSIS_PROMPT.format(
        filename=state.get("file_path", "未命名文件"),
        column_stats=state.get("file_content", "") or "(无列统计)",
        samples="(样本随文件内容附上)",
    )
    return {"answer": get_llm().complete(prompt)}
