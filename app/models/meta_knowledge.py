"""元数据知识库构建（meta_knowledge）。

半自动四步：连接数仓 information_schema / 业务口径映射 / 主外键登记 / 落库。
运行：python -m app.models.meta_knowledge
"""

from typing import Any, Dict, List

from app.models.database import SessionLocal
from app.models.models import MetaKnowledge
from app.repositories.mysql.dw_repository import (
    MOCK_META_COLUMNS, MOCK_META_FOREIGN_KEYS,
)


def _collect_from_dw() -> List[Dict[str, Any]]:
    """真实模式：从数仓 information_schema 收集表/列/主外键。"""
    # TODO(prod): 连 MySQL information_schema 拉全量 schema，
    # 再叠加业务口径映射（"毛利率"→gross_profit_rate）生成登记记录。
    return []


def build_meta_knowledge() -> int:
    """初始化元数据知识库。mock 模式用内置样例；真实模式从数仓收集。"""
    records: List[Dict[str, Any]] = []

    for col in MOCK_META_COLUMNS:
        table, column = col["column"].split(".", 1)
        records.append(MetaKnowledge(
            kind="column", table_name=table, column_name=column,
            chinese_name=col.get("name", ""), example=str(col.get("example", "")),
            formula=col.get("formula", ""),
        ))

    for fk in MOCK_META_FOREIGN_KEYS:
        records.append(MetaKnowledge(
            kind="foreign_key", table_name=fk["table"], column_name=fk["fk"],
            chinese_name="主外键", note=f"ref {fk['ref']}",
        ))

    with SessionLocal() as session:
        session.query(MetaKnowledge).delete()
        session.add_all(records)
        session.commit()
    return len(records)


if __name__ == "__main__":
    n = build_meta_knowledge()
    print(f"元数据知识库初始化完成：{n} 条记录（SQLite: {SessionLocal.kw.get('bind')}）")
