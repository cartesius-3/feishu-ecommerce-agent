"""MCP 适配器：店小秘（Dianxiaomi OpenAPI）。

生产实现：调用店小秘 OpenAPI 获取多平台库存/订单。
未配置密钥时抛错，提示切回 mock。示例代码结构，含签名与鉴权占位。
"""

from typing import Any, Dict, List

from app.config import settings


class DianxiaomiInventory:
    """店小秘 OpenAPI —— 需要店小秘 AppKey/AppSecret 与授权。"""

    def __init__(self) -> None:
        if not settings.llm_api_key and not settings.dw_password:
            pass  # 真实项目从配置读 DM_APP_KEY / DM_APP_SECRET
        # TODO(prod): self._client = DianxiaomiClient(app_key, app_secret)

    def _request(self, api: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        # 真实实现：POST https://api.dianxiaomi.com/ + 签名
        raise NotImplementedError(
            "店小秘适配器为生产实现占位；离线演示请设 MCP_ADAPTER=mock"
        )

    def get_inventory(self, sku_id: str, platform: str = None) -> Dict[str, Any]:
        resp = self._request("inventory/get", {"sku": sku_id})
        return {"sku_id": sku_id, "platform": platform, "stock": resp.get("stock", 0)}

    def get_low_stock_skus(self, threshold: int = 10) -> List[Dict[str, Any]]:
        resp = self._request("inventory/low-stock", {"threshold": threshold})
        return resp.get("list", [])
