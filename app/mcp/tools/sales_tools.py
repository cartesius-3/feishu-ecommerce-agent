"""MCP 工具：销售（get_sales_velocity / get_sales_by_region / get_ads_performance）。"""

from typing import Any, Dict, List

from app.mcp.adapters import get_current_adapter


def get_sales_velocity(sku_id: str, days: int = 7) -> Dict[str, Any]:
    """查询 SKU 近 N 天的日均销量和趋势。"""
    adapter = get_current_adapter()
    return adapter.sales.get_sales_velocity(sku_id, days)


def get_sales_by_region(region: str, date_range: str) -> Dict[str, Any]:
    """按区域统计销售额。"""
    adapter = get_current_adapter()
    return adapter.sales.get_sales_by_region(region, date_range)


def get_ads_performance(channel: str = "全部") -> List[Dict[str, Any]]:
    """查询广告投放表现（渠道维度，含 ROI/ROAS）。"""
    adapter = get_current_adapter()
    return adapter.sales.get_ads_performance(channel)
