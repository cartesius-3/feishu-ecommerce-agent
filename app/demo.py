"""命令行体验 Agent（mock 模式，无需任何 Key）。

运行：python -m app.demo
覆盖四条代表性链路：
  1. data_query：NL2SQL 12 节点管线（真实 EXPLAIN + 执行）
  2. product：商品 skill（MCP 工具）
  3. content：文案生成
  4. help：能力介绍
"""

import json

from app.agent.workflow import build_graph


def run_one(graph, text: str, cid: str = "demo") -> None:
    print(f"\n{'=' * 60}\n[用户] {text}")
    state = graph.invoke({"user_input": text, "conversation_id": cid})
    print(f"[意图] {state.get('intent')}")
    if state.get("generated_sql"):
        print(f"[SQL] {state['generated_sql']}")
    if state.get("query_result"):
        print(f"[结果] {len(state['query_result'])} 行")
    print(f"[Agent] {state.get('answer', '(空)')}")


def main() -> None:
    graph = build_graph()
    cases = [
        "华东区毛利率超过40%的SKU有哪些？",
        "SKU001最近一周卖了多少？",
        "写个小红书种草文案",
        "你能做什么？",
    ]
    for case in cases:
        run_one(graph, case)
    print(f"\n{'=' * 60}\n[完成] 全链路演示完成（mock 模式）")


if __name__ == "__main__":
    main()
