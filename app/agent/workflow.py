"""LangGraph StateGraph 构建。

图结构（对齐技术文档 2.2 / 2.3）：

  START → load_history → load_file → intent_router ──条件边──▶ 各子图
     data_query → extract_keywords → recall_column/value/metric(并行)
        → merge_retrieved → filter_schema → add_context → generate_sql
        → validate_sql ──条件边──▶ error=None → run_sql
                                └▶ error≠None → correct_sql → run_sql
        → answer → save_history → END
     product/ads/content/file/help → 对应 skill → answer → save_history → END

条件边设计原则：业务规则用条件边（确定性判断），语义理解用 LLM 路由。
"""

from langgraph.graph import END, START, StateGraph

from app.agent.intent_router import intent_router
from app.agent.nodes.answer import answer_node
from app.agent.nodes.extract_keywords import extract_keywords
from app.agent.nodes.recall_column import recall_column
from app.agent.nodes.recall_value import recall_value
from app.agent.nodes.recall_metric import recall_metric
from app.agent.nodes.merge_retrieved import merge_retrieved_info
from app.agent.nodes.filter_schema import filter_table_and_metric
from app.agent.nodes.add_context import add_extra_context
from app.agent.nodes.generate_sql import generate_sql
from app.agent.nodes.validate_sql import validate_sql
from app.agent.nodes.correct_sql import correct_sql
from app.agent.nodes.run_sql import run_sql
from app.agent.state import AgentState
from app.memory.local_memory import load_history, save_history
from app.tools.file_parser_tool import load_file
from app.skills.product_skill import product_skill
from app.skills.ads_skill import ads_skill
from app.skills.content_skill import content_skill
from app.skills.file_analysis_skill import file_analysis_skill
from app.skills.help_skill import help_skill

# ---------------------------------------------------------------------------
# 条件边路由函数（只读 state 不分拣，返回下一站节点名）
# ---------------------------------------------------------------------------


def route_after_intent(state: AgentState) -> str:
    """意图分发：读 state['intent']，返回对应子图入口节点名。"""
    return {
        "data_query": "extract_keywords",
        "product": "product_skill",
        "ads": "ads_skill",
        "content": "content_skill",
        "file": "file_analysis_skill",
        "help": "help_skill",
    }.get(state.get("intent", "help"), "help_skill")


def route_after_validate(state: AgentState) -> str:
    """SQL 校验分支：读 state['sql_error']（None=成功）。"""
    return "run_sql" if state.get("sql_error") is None else "correct_sql"


# ---------------------------------------------------------------------------
# 图构建
# ---------------------------------------------------------------------------


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # 通用节点
    graph.add_node("load_history", load_history)
    graph.add_node("load_file", load_file)
    graph.add_node("intent_router", intent_router)

    # NL2SQL 管线节点
    graph.add_node("extract_keywords", extract_keywords)
    graph.add_node("recall_column", recall_column)
    graph.add_node("recall_value", recall_value)
    graph.add_node("recall_metric", recall_metric)
    graph.add_node("merge_retrieved", merge_retrieved_info)
    graph.add_node("filter_schema", filter_table_and_metric)
    graph.add_node("add_context", add_extra_context)
    graph.add_node("generate_sql", generate_sql)
    graph.add_node("validate_sql", validate_sql)
    graph.add_node("correct_sql", correct_sql)
    graph.add_node("run_sql", run_sql)

    # 业务 Skill 节点
    graph.add_node("product_skill", product_skill)
    graph.add_node("ads_skill", ads_skill)
    graph.add_node("content_skill", content_skill)
    graph.add_node("file_analysis_skill", file_analysis_skill)
    graph.add_node("help_skill", help_skill)

    # 通用收尾
    graph.add_node("answer", answer_node)
    graph.add_node("save_history", save_history)

    # ---- 主线 ----
    graph.add_edge(START, "load_history")
    graph.add_edge("load_history", "load_file")
    graph.add_edge("load_file", "intent_router")

    # ---- 意图分发（条件边）----
    graph.add_conditional_edges(
        "intent_router",
        route_after_intent,
        {
            "extract_keywords": "extract_keywords",
            "product_skill": "product_skill",
            "ads_skill": "ads_skill",
            "content_skill": "content_skill",
            "file_analysis_skill": "file_analysis_skill",
            "help_skill": "help_skill",
        },
    )

    # ---- NL2SQL 管线 ----
    graph.add_edge("extract_keywords", "recall_column")
    graph.add_edge("extract_keywords", "recall_value")
    graph.add_edge("extract_keywords", "recall_metric")
    graph.add_edge("recall_column", "merge_retrieved")
    graph.add_edge("recall_value", "merge_retrieved")
    graph.add_edge("recall_metric", "merge_retrieved")
    graph.add_edge("merge_retrieved", "filter_schema")
    graph.add_edge("filter_schema", "add_context")
    graph.add_edge("add_context", "generate_sql")
    graph.add_edge("generate_sql", "validate_sql")

    # ---- SQL 校验分支（条件边）----
    graph.add_conditional_edges(
        "validate_sql",
        route_after_validate,
        {"run_sql": "run_sql", "correct_sql": "correct_sql"},
    )
    graph.add_edge("correct_sql", "run_sql")

    # ---- 收尾 ----
    # data_query 结果走 answer_node 转自然语言；skill 路径自带 answer，直接落库
    graph.add_edge("run_sql", "answer")
    for skill in ("product_skill", "ads_skill", "content_skill",
                  "file_analysis_skill", "help_skill"):
        graph.add_edge(skill, "save_history")
    graph.add_edge("answer", "save_history")
    graph.add_edge("save_history", END)

    return graph.compile()
