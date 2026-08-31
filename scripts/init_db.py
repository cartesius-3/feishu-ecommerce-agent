"""初始化业务数据库（SQLite 表结构 + 元数据知识库）。

运行：python -m scripts.init_db
"""

from app.models.database import init_db
from app.models.meta_knowledge import build_meta_knowledge


def main() -> None:
    init_db()
    print("业务库表结构初始化完成（SQLite）")
    n = build_meta_knowledge()
    print(f"元数据知识库初始化完成：{n} 条")


if __name__ == "__main__":
    main()
