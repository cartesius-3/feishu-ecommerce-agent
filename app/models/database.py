"""SQLAlchemy Engine 初始化（业务库 SQLite + 数仓 MySQL）。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

# 业务库（SQLite）：会话、反馈、元数据登记
engine = create_engine(f"sqlite:///{settings.sqlite_path}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    from app.models import models  # noqa: F401 —— 注册表结构

    models.Base.metadata.create_all(bind=engine)
