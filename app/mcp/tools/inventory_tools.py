"""MCP 工具：库存（get_inventory / get_low_stock_skus）。

工具签名稳定，实现走适配器——Mock/店小秘/领星一键切换。
"""

from typing import Any, Dict, List

from app.mcp.adapters import get_current_adapter


def get_inventory(sku_id: str, platform: str = None) -> Dict[str, Any]:
    """查询指定 SKU 在各平台的实时库存。"""
    adapter = get_current_adapter()
    return adapter.inventory.get_inventory(sku_id, platform)


def get_low_stock_skus(threshold: int = 10) -> List[Dict[str, Any]]:
    """查询库存低于阈值的所有 SKU（库存预警用）。"""
    adapter = get_current_adapter()
    return adapter.inventory.get_low_stock_skus(threshold)
