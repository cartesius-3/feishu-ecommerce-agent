"""ORM 模型：4 张业务表 + meta 表。

业务表：conversation（会话）/ feedback（反馈）/ alert（告警）/ metric_record（指标记录）
meta 表：meta_knowledge（元数据知识库登记——字段/指标/主外键）
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Conversation(Base):
    __tablename__ = "conversation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), index=True, nullable=False)
    user_input = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    intent = Column(String(32), default="")
    created_at = Column(DateTime, default=datetime.now)


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), index=True)
    message_id = Column(String(64), default="")
    rating = Column(Integer, default=0)          # 1 有用 / -1 没用 / 0 未评
    comment = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)


class Alert(Base):
    __tablename__ = "alert"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String(32), default="low_stock")
    sku_id = Column(String(32), default="")
    message = Column(Text, default="")
    level = Column(String(16), default="warning")
    created_at = Column(DateTime, default=datetime.now)


class MetricRecord(Base):
    """指标日记录（监控看板数据源）。"""
    __tablename__ = "metric_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric = Column(String(64), index=True)      # llm_calls / db_queries / success_rate…
    value = Column(Float, default=0.0)
    extra = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.now)


class MetaKnowledge(Base):
    """元数据知识库登记表：字段中文含义/取值示例/指标口径/主外键。"""
    __tablename__ = "meta_knowledge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kind = Column(String(16), default="column")   # column | metric | foreign_key
    table_name = Column(String(64), default="")
    column_name = Column(String(64), default="")
    chinese_name = Column(String(64), default="")
    example = Column(String(255), default="")
    formula = Column(String(255), default="")
    note = Column(Text, default="")
