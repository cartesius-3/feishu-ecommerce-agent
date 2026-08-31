"""MCP 适配器：Mock（内存实现，离线演示）。

真实数据源切换只改 MCP_ADAPTER 配置，Agent 图与工具签名不动——
这就是工具与 Agent 解耦。
"""

import random
from typing import Any, Dict, List

# 内存"库存"样例（SKU -> {平台 -> 库存}）
_MOCK_INVENTORY: Dict[str, Dict[str, int]] = {
    "SKU001": {"自营": 320, "天猫": 45, "京东": 60},
    "SKU002": {"自营": 12, "天猫": 8, "京东": 0},
    "SKU003": {"自营": 210, "天猫": 90, "京东": 75},
    "SKU004": {"自营": 5, "天猫": 2, "京东": 1},
}

_SAFE_STOCK_THRESHOLD = 10


class MockInventory:
    def get_inventory(self, sku_id: str, platform: str = None) -> Dict[str, Any]:
        inv = _MOCK_INVENTORY.get(sku_id, {})
        if platform:
            return {"sku_id": sku_id, "platform": platform, "stock": inv.get(platform, 0)}
        return {"sku_id": sku_id, "platforms": inv, "total": sum(inv.values())}

    def get_low_stock_skus(self, threshold: int = _SAFE_STOCK_THRESHOLD) -> List[Dict[str, Any]]:
        low = []
        for sku_id, inv in _MOCK_INVENTORY.items():
            total = sum(inv.values())
            if total <= threshold:
                low.append({"sku_id": sku_id, "total_stock": total, "by_platform": inv})
        return low


class MockSales:
    def get_sales_velocity(self, sku_id: str, days: int = 7) -> Dict[str, Any]:
        base = {"SKU001": 32, "SKU002": 18, "SKU003": 25, "SKU004": 12}.get(sku_id, 15)
        trend = [round(base * random.uniform(0.7, 1.3), 1) for _ in range(days)]
        return {"sku_id": sku_id, "days": days, "daily_sales": trend,
                "avg_daily": round(sum(trend) / len(trend), 1),
                "total": round(sum(trend), 1)}

    def get_sales_by_region(self, region: str, date_range: str) -> Dict[str, Any]:
        return {"region": region, "date_range": date_range,
                "gmv": round(random.uniform(5e5, 5e6), 2), "orders": random.randint(500, 5000)}

    def get_ads_performance(self, channel: str = "全部") -> List[Dict[str, Any]]:
        channels = ["搜索", "信息流", "短视频", "直播"]
        rows = []
        for ch in channels:
            if channel != "全部" and ch != channel:
                continue
            ad_cost = round(random.uniform(1e4, 1e5), 2)
            revenue = ad_cost * random.uniform(1.0, 5.5)
            rows.append({
                "channel": ch,
                "ad_cost": ad_cost,
                "revenue": round(revenue, 2),
                "roi": round(revenue / ad_cost, 2),
                "roas": round(revenue / ad_cost, 2),
                "clicks": random.randint(1e4, 1e5),
                "ctr": round(random.uniform(0.01, 0.06), 4),
            })
        return rows


class MockOrder:
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        statuses = ["待发货", "运输中", "已签收", "退款中"]
        return {"order_id": order_id, "status": random.choice(statuses),
                "updated_at": "2026-08-07 18:30:00"}


class MockAlert:
    def send_alert(self, chat_id: str, title: str, message: str, level: str = "info") -> Dict[str, Any]:
        # mock：打印到控制台，模拟飞书群告警 + 多维表格记录
        print(f"[MOCK-ALERT] {level.upper()} | {title}: {message}")
        return {"ok": True, "chat_id": chat_id, "title": title}


class MockAdapter:
    inventory = MockInventory()
    sales = MockSales()
    order = MockOrder()
    alert = MockAlert()
