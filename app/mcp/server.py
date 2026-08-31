"""MCP Server 组装（FastMCP）。

真实部署：把工具函数注册到 FastMCP server，供外部 MCP 客户端（如 Dify/Claude）
按 tools/list + tools/call 协议调用。Agent 图内则直接 import 工具函数，
不依赖 server 进程——两种接入方式并存。

运行：python -m app.mcp.server
"""

from app.config import settings


def build_mcp():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        raise RuntimeError("需要安装 fastmcp；Agent 图内直调不需要启动 server")

    mcp = FastMCP("ecommerce-tools")

    # 库存工具
    from app.mcp.tools.inventory_tools import get_inventory, get_low_stock_skus

    mcp.tool()(get_inventory)
    mcp.tool()(get_low_stock_skus)

    # 销售工具
    from app.mcp.tools.sales_tools import get_sales_velocity, get_sales_by_region, get_ads_performance

    mcp.tool()(get_sales_velocity)
    mcp.tool()(get_sales_by_region)
    mcp.tool()(get_ads_performance)

    # 订单工具
    from app.mcp.tools.order_tools import get_order_status

    mcp.tool()(get_order_status)

    # 告警工具
    from app.mcp.tools.alert_tools import send_alert

    mcp.tool()(send_alert)

    return mcp


if __name__ == "__main__":
    mcp = build_mcp()
    mcp.run(transport="stdio")
