"""FastAPI 入口。

- POST /api/chat        —— 单轮对话（Agent 执行）
- GET  /api/health      —— 健康检查（数仓/依赖探活）
- startup              —— 启动飞书 WS 独立子进程（FEISHU_WS_ENABLED=true 时）
- APScheduler          —— 库存预警扫描 + 看板同步
"""

import subprocess
import sys
from typing import Any, Dict

from fastapi import FastAPI
from pydantic import BaseModel

from app.config import settings
from app.models.database import init_db

app = FastAPI(title="飞书 AI 电商数据助手 Agent", version="1.0.0")


class ChatRequest(BaseModel):
    user_input: str
    conversation_id: str = "default"
    file_path: str = ""


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    # 飞书 WS 独立子进程：主进程挂了不影响消息接收
    if settings.feishu_ws_enabled:
        subprocess.Popen(
            [sys.executable, "-m", "app.tools.feishu_ws"],
            stdout=sys.stdout, stderr=sys.stderr,
        )
    _start_scheduler()


def _start_scheduler() -> None:
    """定时任务：库存预警扫描 + 看板同步（每小时）。"""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        from app.monitoring.dashboard import sync_metrics_to_bitable
        from app.mcp.tools.inventory_tools import get_low_stock_skus
        from app.mcp.tools.alert_tools import send_alert

        scheduler = BackgroundScheduler()

        def stock_scan() -> None:
            for item in get_low_stock_skus(threshold=10):
                send_alert("monitor_group", "库存预警",
                           f"{item['sku_id']} 库存 {item['total_stock']}，低于安全阈值",
                           level="warning")

        scheduler.add_job(stock_scan, "interval", minutes=30)
        scheduler.add_job(sync_metrics_to_bitable, "interval", hours=1)
        scheduler.start()
    except ImportError:
        print("[main] APScheduler 未安装，跳过定时任务")


@app.post("/api/chat")
def chat(req: ChatRequest) -> Dict[str, Any]:
    from app.agent.workflow import build_graph
    from app.monitoring.stats import monitoring_stats
    from app.tools.guardrails import check_input

    if reason := check_input(req.user_input):
        return {"answer": f"⚠️ {reason}", "intent": "blocked"}

    graph = build_graph()
    with monitoring_stats.timer("agent_total"):
        state = graph.invoke({
            "user_input": req.user_input,
            "conversation_id": req.conversation_id,
            "file_path": req.file_path,
        })
    monitoring_stats.record_intent(state.get("intent", "unknown"))
    return {
        "answer": state.get("answer", ""),
        "intent": state.get("intent", ""),
        "sql": state.get("generated_sql", ""),
        "trace": _trace_summary(state),
    }


def _trace_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    """轻量轨迹摘要（节点级 Tracing 完整版见 tracing 模块/前端面板）。"""
    return {
        "keywords": state.get("keywords", [])[:5],
        "recalled_columns": len(state.get("retrieved_columns", [])),
        "recalled_values": len(state.get("retrieved_values", [])),
        "recalled_metrics": len(state.get("retrieved_metrics", [])),
        "rows": len(state.get("query_result", [])),
    }


@app.get("/api/health")
def health() -> Dict[str, Any]:
    from app.repositories.mysql.dw_repository import get_dw_repository

    try:
        dw = get_dw_repository()
        ok = bool(dw.query("SELECT 1 AS ok"))
        return {"status": "ok", "dw": "ok" if ok else "error",
                "mode": {"llm": settings.llm_mode, "dw": settings.dw_mode}}
    except Exception as e:  # noqa: BLE001
        return {"status": "degraded", "dw": "error", "detail": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
