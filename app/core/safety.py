"""NL2SQL 五层安全防护。

| 层 | 方法 | 位置 |
|----|------|------|
| 1 | Prompt 约束 | generate_sql prompt（"只能生成 SELECT…"）|
| 2 | 正则黑名单 | 本文件 enforce_read_only |
| 3 | SQLGlot AST 解析 | 本文件 enforce_read_only（parse_one().key == select）|
| 4 | EXPLAIN 真实校验 | validate_sql 节点（数据库引擎真报错）|
| 5 | 只读数据库账号 | config.dw_user（READ ONLY MySQL 用户）|
"""

import re
from typing import Optional

_BLACKLIST_RE = re.compile(r"\b(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXEC|CALL)\b", re.IGNORECASE)


def enforce_read_only(sql: str) -> Optional[str]:
    """层 2+3：正则黑名单 + SQLGlot AST。返回错误信息，通过返回 None。"""
    if not sql or not sql.strip():
        return "EmptySQL"
    if _BLACKLIST_RE.search(sql):
        return "SecurityError: forbidden keyword detected"
    try:
        import sqlglot

        ast = sqlglot.parse_one(sql)
        if ast.key.upper() != "SELECT":
            return "SecurityError: only SELECT statements are allowed"
    except ImportError:
        # 未安装 sqlglot：退化为正则判断（非 SELECT 开头即拒绝）
        if not re.match(r"^\s*(SELECT|WITH)", sql, re.IGNORECASE):
            return "SecurityError: only SELECT statements are allowed"
    except Exception:  # noqa: BLE001 —— 语法解析失败一律拒绝
        return "SyntaxError: invalid SQL"
    return None
