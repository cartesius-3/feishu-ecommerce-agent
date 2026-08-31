"""MCP 工具：告警（send_alert）。

向飞书群发送告警消息 + 写入多维表格告警记录（库存预警等场景）。
"""

from typing import Any, Dict

from app.mcp.adapters import get_current_adapter


def send_alert(chat_id: str, title: str, message: str, level: str = "info") -> Dict[str, Any]:
    """向飞书群发送告警消息 + 写多维表格告警记录。"""
    adapter = get_current_adapter()
    return adapter.alert.send_alert(chat_id, title, message, level)
