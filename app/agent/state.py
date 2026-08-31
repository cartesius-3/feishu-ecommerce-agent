"""LangGraph 共享状态（AgentState）。

字段设计对齐技术文档 2.1 节：通用字段 + NL2SQL 专用字段。
LangGraph 条件边只读这些 state 字段，不重新判断。
"""

from typing import Any, Dict, List, TypedDict


class AgentState(TypedDict, total=False):
    # ---------- 通用字段 ----------
    user_input: str                  # 用户输入文本
    conversation_id: str             # 会话ID（飞书 chat_id）
    history: List[Dict[str, Any]]    # 最近 10 条对话历史
    tool_result: Dict[str, Any]      # 路由结果 + Skill/NL2SQL 执行结果
    answer: str                      # 最终回复文本
    intent: str                      # 识别到的意图 (data_query/product/ads/content/file/help)
    token_usage: Dict[str, int]      # Token 消耗统计
    file_path: str                   # 上传文件路径
    file_content: str                # 解析后的文件内容

    # ---------- NL2SQL 专用字段 ----------
    keywords: List[str]              # jieba 提取的关键词
    retrieved_columns: List[Dict[str, Any]]   # Milvus 召回的字段信息
    retrieved_values: List[Dict[str, Any]]    # ES 召回的取值信息
    retrieved_metrics: List[Dict[str, Any]]   # Milvus 召回的指标信息
    merged_schema: Dict[str, Any]    # 合并过滤后的候选 schema（表 + 指标）
    generated_sql: str               # LLM 生成的 SQL
    sql_error: str                   # EXPLAIN 校验错误信息（None=成功）
    query_result: List[Dict[str, Any]]  # SQL 执行结果
