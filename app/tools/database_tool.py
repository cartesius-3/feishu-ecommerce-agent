"""数据库查询工具（database_tool）。

升级前有 8 种写死的 SQL 方法（get_product_sales/get_ads_performance 等）；
升级后统一走动态 NL2SQL 管线，这里仅保留只读查询能力作兜底。
"""

from typing import Any, Dict, List

from app.repositories.mysql.dw_repository import get_dw_repository


class DatabaseTool:
    """只读 SQL 查询工具（无写操作）。"""

    def query(self, sql: str) -> List[Dict[str, Any]]:
        dw = get_dw_repository()
        return dw.query(sql)

    def ping(self) -> Dict[str, Any]:
        try:
            dw = get_dw_repository()
            result = dw.query("SELECT 1 AS ok")
            return {"ok": bool(result) and result[0].get("ok") == 1}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}


database_tool = DatabaseTool()
