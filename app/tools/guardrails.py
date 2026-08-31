"""输入安全（Guardrails）。

- 输入长度限制（防 token 爆炸）
- 敏感词/注入模式过滤（防 prompt 注入）
- 消息解密（AES，飞书加密模式）
"""

import re
from typing import Optional

from app.config import settings

# prompt 注入常见模式（示例级，生产可扩展）
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts)",
    r"你(现在|必须|请).{0,20}(忘记|忽略).{0,20}(指令|规则|prompt)",
    r"system\s*prompt",
]


class Guardrails:
    def check_input(self, text: str) -> Optional[str]:
        """返回 None=通过；返回 str=被拦截原因。"""
        if len(text) > settings.max_input_chars:
            return f"输入过长（>{settings.max_input_chars} 字符）"
        for pattern in _INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return "检测到疑似注入内容，已拦截"
        return None


_guardrails = Guardrails()


def check_input(text: str) -> Optional[str]:
    if not settings.guardrails_enabled:
        return None
    return _guardrails.check_input(text)
