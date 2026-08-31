"""数仓访问层（数据仓储）。

- dw_mode=mock：SQLite 内存数仓。预置 4 张事实/维度表 + 样例数据，
  EXPLAIN 与 SELECT 都是真实执行——NL2SQL 管线在 mock 下完整可跑。
- dw_mode=mysql：SQLAlchemy 异步连接真实 MySQL，只读账号兜底。

对外两个核心能力：validate(sql) 做 EXPLAIN 校验、query(sql) 执行只读查询。
"""

import re
import sqlite3
from typing import Any, Dict, List, Optional

from app.config import settings

# ---------------------------------------------------------------------------
# Mock 数仓：SQLite 内存 + 样例表结构
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE dim_product (
    sku_code TEXT PRIMARY KEY,
    product_name TEXT,
    category TEXT,
    brand TEXT,
    standard_cost REAL
);
CREATE TABLE dim_region (
    region_id INTEGER PRIMARY KEY,
    region_name TEXT,
    province TEXT
);
CREATE TABLE dim_date (
    dt TEXT PRIMARY KEY
);
CREATE TABLE fact_order (
    order_id INTEGER PRIMARY KEY,
    dt TEXT,
    sku_code TEXT,
    region_id INTEGER,
    quantity INTEGER,
    amount REAL,
    profit_margin REAL,
    gross_profit_rate REAL
);
"""

_MOCK_ROWS = {
    "dim_product": [
        ("SKU001", "无线蓝牙耳机 Pro", "数码", "声阔", 99.0),
        ("SKU002", "便携充电宝 20000mAh", "数码", "倍思", 49.0),
        ("SKU003", "智能手环 5 代", "穿戴", "小米", 159.0),
        ("SKU004", "电动牙刷 T5", "个护", "飞利浦", 199.0),
    ],
    "dim_region": [
        (1, "华东", "上海"),
        (2, "华南", "广东"),
        (3, "华北", "北京"),
    ],
    "fact_order": [
        (1001, "2026-08-01", "SKU001", 1, 20, 1399.0, 0.32, 32.0),
        (1002, "2026-08-01", "SKU002", 1, 50, 745.0, 0.28, 28.0),
        (1003, "2026-08-02", "SKU001", 1, 30, 2098.5, 0.35, 35.0),
        (1004, "2026-08-03", "SKU003", 1, 40, 1590.0, 0.30, 30.0),
        (1005, "2026-08-04", "SKU002", 1, 25, 372.5, 0.22, 22.0),
        (1006, "2026-08-05", "SKU004", 1, 18, 1791.0, 0.41, 41.0),
        (1007, "2026-08-06", "SKU001", 1, 45, 3147.75, 0.38, 38.0),
        (1008, "2026-08-07", "SKU003", 1, 22, 874.5, 0.26, 26.0),
    ],
    "dim_date": [("2026-08-01",), ("2026-08-02",), ("2026-08-03",),
                 ("2026-08-04",), ("2026-08-05",), ("2026-08-06",), ("2026-08-07",)],
}

# 与 mock 数仓对应的元数据知识库（字段语义 / 取值示例 / 主外键）
MOCK_META_COLUMNS: List[Dict[str, Any]] = [
    {"column": "fact_order.amount", "name": "销售额", "table": "fact_order",
     "metric": "gmv", "example": 2098.5},
    {"column": "fact_order.quantity", "name": "销量", "table": "fact_order",
     "metric": "sales_quantity", "example": 30},
    {"column": "fact_order.gross_profit_rate", "name": "毛利率", "table": "fact_order",
     "metric": "gross_margin", "formula": "(revenue-cost)/revenue*100", "example": 35.0},
    {"column": "dim_product.sku_code", "name": "SKU编码", "table": "dim_product",
     "example": "SKU001"},
    {"column": "dim_product.product_name", "name": "商品名称", "table": "dim_product",
     "example": "无线蓝牙耳机 Pro"},
    {"column": "dim_region.region_name", "name": "区域", "table": "dim_region",
     "example": "华东"},
]

MOCK_META_FOREIGN_KEYS = [
    {"table": "fact_order", "fk": "sku_code", "ref": "dim_product.sku_code"},
    {"table": "fact_order", "fk": "region_id", "ref": "dim_region.region_id"},
    {"table": "fact_order", "fk": "dt", "ref": "dim_date.dt"},
]


class MockDwRepository:
    """SQLite 内存数仓：EXPLAIN / SELECT 真实执行。"""

    name = "mock"

    def __init__(self) -> None:
        self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._conn.executescript(_SCHEMA_SQL)
        for table, rows in _MOCK_ROWS.items():
            cols = self._col_names(table)
            if rows:
                placeholders = ", ".join("?" * len(cols))
                self._conn.executemany(
                    f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})", rows
                )
        self._conn.commit()

    def _col_names(self, table: str) -> List[str]:
        cur = self._conn.execute(f"PRAGMA table_info({table})")
        return [r[1] for r in cur.fetchall()]

    def validate(self, sql: str) -> Optional[str]:
        """EXPLAIN 校验：真实连库但不取数。返回错误信息或 None（成功）。"""
        if not self._is_read_only(sql):
            return "SecurityError: only SELECT statements are allowed"
        try:
            self._conn.execute(f"EXPLAIN {sql}")
            return None
        except Exception as e:  # noqa: BLE001 —— 报错信息即为 sql_error
            return str(e)

    def query(self, sql: str) -> List[Dict[str, Any]]:
        if not self._is_read_only(sql):
            raise ValueError("SecurityError: only SELECT statements are allowed")
        cur = self._conn.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    @staticmethod
    def _is_read_only(sql: str) -> bool:
        return bool(re.match(r"^\s*(SELECT|WITH|EXPLAIN)", sql, re.IGNORECASE))


class MysqlDwRepository:
    """真实 MySQL 数仓（异步 SQLAlchemy）。连接使用只读账号。"""

    name = "mysql"

    def __init__(self) -> None:
        import sqlalchemy as sa
        from sqlalchemy.ext.asyncio import create_async_engine

        url = (
            f"mysql+asyncmy://{settings.dw_user}:{settings.dw_password}"
            f"@{settings.dw_host}:{settings.dw_port}/{settings.dw_database}"
        )
        self._engine = create_async_engine(url, pool_size=5, echo=False)

    async def validate(self, sql: str) -> Optional[str]:
        import sqlalchemy as sa

        if not MockDwRepository._is_read_only(sql):
            return "SecurityError: only SELECT statements are allowed"
        try:
            async with self._engine.connect() as conn:
                await conn.execute(sa.text(f"EXPLAIN {sql}"))
            return None
        except Exception as e:  # noqa: BLE001
            return str(e)

    async def query(self, sql: str) -> List[Dict[str, Any]]:
        import sqlalchemy as sa

        if not MockDwRepository._is_read_only(sql):
            raise ValueError("SecurityError: only SELECT statements are allowed")
        async with self._engine.connect() as conn:
            result = await conn.execute(sa.text(sql))
            cols = list(result.keys())
            return [dict(zip(cols, row)) for row in result.fetchall()]


def get_dw_repository():
    """按 dw_mode 返回数仓实现。mock 返回同步 SQLite；mysql 返回异步引擎。"""
    if settings.dw_mode == "mysql":
        return MysqlDwRepository()
    return MockDwRepository()
