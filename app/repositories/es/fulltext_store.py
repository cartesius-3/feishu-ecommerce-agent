"""Elasticsearch 全文检索（取值召回）。

- 真实模式：elasticsearch 客户端 BM25 精确匹配维度值。
- mock 模式：内存匹配 dim_region/dim_product 取值，离线演示。

作用：召回"华东区"→'华东'这类字面取值。
向量对"华东/华北"这类近义维度值容易混淆，取值走全文更准。
"""

from typing import Any, Dict, List

from app.config import settings
from app.repositories.mysql.dw_repository import _MOCK_ROWS


class MockFulltextStore:
    """内存全文库：维度取值精确匹配。"""

    name = "mock"

    def search(self, keyword: str, top_k: int = 5) -> List[Dict[str, Any]]:
        hits = []
        # 区域取值
        for row in _MOCK_ROWS["dim_region"]:
            region_id, region_name, province = row
            if keyword in region_name or keyword in province:
                hits.append({"value": region_name, "field": "dim_region.region_name",
                             "table": "dim_region", "score": 1.0})
        # 商品取值
        for row in _MOCK_ROWS["dim_product"]:
            sku_code, product_name, category, brand, _cost = row
            if keyword in product_name or keyword in category or keyword in brand:
                hits.append({"value": product_name, "field": "dim_product.product_name",
                             "table": "dim_product", "score": 1.0})
                hits.append({"value": sku_code, "field": "dim_product.sku_code",
                             "table": "dim_product", "score": 0.8})
        return hits[:top_k]


class ESFulltextStore:
    """Elasticsearch 真实实现（BM25）。"""

    name = "es"

    def __init__(self) -> None:
        try:
            from elasticsearch import Elasticsearch
        except ImportError:
            raise RuntimeError("需要安装 elasticsearch；离线演示请设 EMBED_MODE=mock")
        self._client = Elasticsearch(settings.es_host)

    def search(self, keyword: str, top_k: int = 5) -> List[Dict[str, Any]]:
        body = {"query": {"multi_match": {"query": keyword, "fields": ["value^2", "table"]}}}
        resp = self._client.search(index="meta_values", body=body, size=top_k)
        return [{"value": h["_source"].get("value"),
                 "field": h["_source"].get("field"),
                 "table": h["_source"].get("table"),
                 "score": h["_score"]} for h in resp["hits"]["hits"]]


_fulltext_store = MockFulltextStore()


def recall_values(keyword: str, top_k: int = 5) -> List[Dict[str, Any]]:
    if settings.embed_mode == "mock":
        return _fulltext_store.search(keyword, top_k)
    store = ESFulltextStore()
    return store.search(keyword, top_k)
