"""全链路监控（MonitoringStats）：LLM/飞书 API/数据库/意图分布/成功率。

各节点通过 with stats.timer("llm_calls") 或 stats.count(...) 打点，
dashboard 每小时把汇总同步到飞书多维表格看板。
"""

import threading
import time
from collections import defaultdict
from typing import Any, Dict, Optional


class MonitoringStats:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._timers: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "total_time": 0.0, "errors": 0}
        )
        self._counters: Dict[str, int] = defaultdict(int)
        self._intent_counts: Dict[str, int] = defaultdict(int)
        self._started_at = time.time()

    # ----- 计时器上下文 -----
    def timer(self, name: str):
        return _Timer(self, name)

    def record_time(self, name: str, seconds: float, error: bool = False) -> None:
        with self._lock:
            entry = self._timers[name]
            entry["count"] += 1
            entry["total_time"] += seconds
            if error:
                entry["errors"] += 1

    def count(self, name: str, n: int = 1) -> None:
        with self._lock:
            self._counters[name] += n

    def record_intent(self, intent: str) -> None:
        with self._lock:
            self._intent_counts[intent] += 1

    # ----- 汇总 -----
    def get_health_status(self) -> Dict[str, Any]:
        with self._lock:
            llm = self._timers["llm_calls"]
            feishu = self._timers["feishu_api_calls"]
            db = self._timers["database_queries"]
            data_query = self._timers["data_query"]
            return {
                "llm_calls": {
                    "count": llm["count"],
                    "avg_time": round(llm["total_time"] / max(llm["count"], 1), 3),
                    "errors": llm["errors"],
                },
                "feishu_api_calls": {
                    "count": feishu["count"],
                    "avg_time": round(feishu["total_time"] / max(feishu["count"], 1), 3),
                },
                "database_queries": {"count": db["count"]},
                "total_tokens": {
                    "prompt": self._counters["tokens_prompt"],
                    "completion": self._counters["tokens_completion"],
                },
                "intent_counts": dict(self._intent_counts),
                "success_rate": round(
                    1 - data_query["errors"] / max(data_query["count"], 1), 4
                ),
                "error_rate": round(
                    sum(t["errors"] for t in self._timers.values()) /
                    max(sum(t["count"] for t in self._timers.values()), 1), 4
                ),
                "uptime_seconds": round(time.time() - self._started_at, 1),
            }


class _Timer:
    def __init__(self, stats: MonitoringStats, name: str) -> None:
        self._stats = stats
        self._name = name
        self._start = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._stats.record_time(self._name, time.perf_counter() - self._start,
                                error=exc_type is not None)


monitoring_stats = MonitoringStats()
