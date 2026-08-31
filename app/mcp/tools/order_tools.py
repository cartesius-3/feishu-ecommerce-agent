"""MCP 工具：订单（get_order_status）。"""

from typing import Any, Dict

from app.mcp.adapters import get_current_adapter


def get_order_status(order_id: str) -> Dict[str, Any]:
    """查询订单当前状态（待发货/运输中/已签收/退款中）。"""
    adapter = get_current_adapter()
    return adapter.order.get_order_status(order_id)
