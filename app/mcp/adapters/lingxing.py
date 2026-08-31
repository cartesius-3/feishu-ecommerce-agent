"""MCP 适配器：领星（Lingxing API）。

生产实现：领星 ERP 开放平台 API（商品/库存/销售报表）。
未配置时抛错提示切 mock。
"""

from typing import Any, Dict, List


class LingxingInventory:
    """领星 API —— 需要 Access Key / Secret Key 签名。"""

    def __init__(self) -> None:
        # TODO(prod): self._client = LingxingClient(access_key, secret_key)
        pass

    def _request(self, api: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError(
            "领星适配器为生产实现占位；离线演示请设 MCP_ADAPTER=mock"
        )

    def get_inventory(self, sku_id: str, platform: str = None) -> Dict[str, Any]:
        resp = self._request("inventory/list", {"sku": sku_id})
        return {"sku_id": sku_id, "platform": platform, "stock": resp.get("available", 0)}

    def get_low_stock_skus(self, threshold: int = 10) -> List[Dict[str, Any]]:
        resp = self._request("inventory/low", {"threshold": threshold})
        return resp.get("items", [])
