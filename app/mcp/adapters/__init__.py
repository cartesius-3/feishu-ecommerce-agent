"""适配器工厂：按 MCP_ADAPTER 配置返回当前数据源适配器门面。

Agent 图里只引用工具函数（get_inventory(sku_id, platform)），
切换 ERP 只改配置，不改任何节点和边。
"""

from functools import lru_cache
from typing import Any

from app.config import settings


class AdapterFacade:
    """统一门面：inventory / sales / order / alert 四组数据源适配器。"""

    def __init__(self, inventory: Any, sales: Any, order: Any, alert: Any) -> None:
        self.inventory = inventory
        self.sales = sales
        self.order = order
        self.alert = alert


@lru_cache
def get_current_adapter() -> AdapterFacade:
    from app.mcp.adapters.mock import (
        MockAdapter, MockAlert, MockInventory, MockOrder, MockSales,
    )

    if settings.mcp_adapter == "mock":
        return AdapterFacade(MockInventory(), MockSales(), MockOrder(), MockAlert())

    if settings.mcp_adapter == "dianxiaomi":
        from app.mcp.adapters.dianxiaomi import DianxiaomiInventory

        return AdapterFacade(DianxiaomiInventory(), MockSales(), MockOrder(), MockAlert())

    if settings.mcp_adapter == "lingxing":
        from app.mcp.adapters.lingxing import LingxingInventory

        return AdapterFacade(LingxingInventory(), MockSales(), MockOrder(), MockAlert())

    # 兜底：默认 mock
    return AdapterFacade(MockInventory(), MockSales(), MockOrder(), MockAlert())
