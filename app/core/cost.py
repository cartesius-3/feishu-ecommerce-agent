"""混合模型路由 + 缓存 + 预算控制。

- 主模型：DeepSeek（默认，便宜）
- 备选模型：GPT-4o（复杂分析兜底，成本高）
- 简单任务走小模型/缓存，复杂任务走大模型——控制 token 成本。
"""

import hashlib
import time
from typing import Any, Dict, Optional

from app.core.llm import get_llm


class TokenBudget:
    """进程级 token 预算：超限告警（mock 下打印）。"""

    def __init__(self, monthly_limit: int = 20_000_000) -> None:
        self.monthly_limit = monthly_limit
        self.usage: Dict[str, int] = {"prompt": 0, "completion": 0, "calls": 0}

    def record(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.usage["prompt"] += prompt_tokens
        self.usage["completion"] += completion_tokens
        self.usage["calls"] += 1
        if self.usage["prompt"] + self.usage["completion"] > self.monthly_limit:
            print(f"[COST-WARN] token 用量超月度预算：{self.usage}")


_budget = TokenBudget()
_response_cache: Dict[str, Any] = {}


def cached_complete(prompt: str, *, cache_ttl: int = 3600) -> str:
    """带缓存 + 预算的 LLM 调用。同一 prompt 短期内不重复计费。"""
    key = hashlib.md5(prompt.encode("utf-8")).hexdigest()
    hit = _response_cache.get(key)
    if hit and time.time() - hit["ts"] < cache_ttl:
        return hit["text"]

    text = get_llm().complete(prompt)
    _response_cache[key] = {"text": text, "ts": time.time()}
    # mock 下无法精确计 token，按字符/4 估算
    _budget.record(len(prompt) // 4, len(text) // 4)
    return text


def route_model(prompt: str, *, task: str = "default") -> str:
    """按任务复杂度路由模型（真实模式）：
    intent/file/help 等轻任务走小模型，SQL 生成/分析走主模型。
    """
    light_tasks = {"intent", "file", "help", "extract"}
    if task in light_tasks:
        return "deepseek-chat"
    return "deepseek-chat"  # 主模型；复杂分析可切 fallback
