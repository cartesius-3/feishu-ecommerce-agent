"""监控看板：每小时同步 MonitoringStats 到飞书多维表格。

看板字段：LLM 调用次数/耗时/错误、飞书 API 调用、数据库查询、
Token 消耗、意图分布、NL2SQL 成功率、错误率。
"""

import json
from datetime import datetime

from app.monitoring.stats import monitoring_stats
from app.tools.feishu_tool import feishu_tool


def sync_metrics_to_bitable() -> dict:
    """每小时同步到飞书多维表格（APScheduler 定时触发）。"""
    stats = monitoring_stats.get_health_status()
    records = {
        "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "LLM调用次数": stats["llm_calls"]["count"],
        "LLM平均耗时(ms)": round(stats["llm_calls"]["avg_time"] * 1000, 1),
        "LLM错误数": stats["llm_calls"]["errors"],
        "飞书API调用": stats["feishu_api_calls"]["count"],
        "数据库查询": stats["database_queries"]["count"],
        "Token消耗(prompt)": stats["total_tokens"]["prompt"],
        "Token消耗(completion)": stats["total_tokens"]["completion"],
        "NL2SQL成功率": stats["success_rate"],
        "意图分布": json.dumps(stats["intent_counts"], ensure_ascii=False),
        "错误率": stats["error_rate"],
    }
    return feishu_tool.sync_to_bitable(records)
