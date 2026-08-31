"""飞书 AI 电商数据助手 Agent — 全局配置

环境变量 → Pydantic 模型。所有外部服务（LLM / Embedding / ERP / 数仓）
都支持 mock 模式，mock 下无需任何 API Key 即可跑通全链路演示。
"""

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """全局配置。字段注释标明对应环境变量（env 前缀省略）。"""

    # ---------- 运行模式 ----------
    # mock: 离线演示（默认） | deepseek: DeepSeek API | openai: OpenAI 兼容 API
    llm_mode: str = Field("mock", alias="LLM_MODE")
    # mock: 内存检索 | tei: 远程 TEI 服务 | local: 本地 MiniLM
    embed_mode: str = Field("mock", alias="EMBED_MODE")
    # mock: 内存适配器 | dianxiaomi: 店小秘 OpenAPI | lingxing: 领星 API
    mcp_adapter: str = Field("mock", alias="MCP_ADAPTER")
    # mock: SQLite 内存数仓 | mysql: 真实 MySQL 数仓
    dw_mode: str = Field("mock", alias="DW_MODE")

    # ---------- LLM ----------
    llm_model: str = Field("deepseek-chat", alias="LLM_MODEL")
    llm_base_url: str = Field("https://api.deepseek.com", alias="LLM_BASE_URL")
    llm_api_key: str = Field("", alias="LLM_API_KEY")
    llm_temperature: float = Field(0.0, alias="LLM_TEMPERATURE")
    # 复杂分析兜底模型
    fallback_model: str = Field("gpt-4o", alias="FALLBACK_MODEL")
    fallback_base_url: str = Field("", alias="FALLBACK_BASE_URL")
    fallback_api_key: str = Field("", alias="FALLBACK_API_KEY")

    # ---------- Embedding ----------
    embedding_model: str = Field("BAAI/bge-large-zh-v1.5", alias="EMBEDDING_MODEL")
    embedding_dim: int = Field(1024, alias="EMBEDDING_DIM")
    tei_base_url: str = Field("http://localhost:8080", alias="TEI_BASE_URL")
    local_embed_model: str = Field("paraphrase-multilingual-MiniLM-L12-v2", alias="LOCAL_EMBED_MODEL")

    # ---------- 数仓 (MySQL) ----------
    dw_host: str = Field("localhost", alias="DW_HOST")
    dw_port: int = Field(3306, alias="DW_PORT")
    dw_user: str = Field("readonly", alias="DW_USER")          # 只读账号兜底
    dw_password: str = Field("", alias="DW_PASSWORD")
    dw_database: str = Field("ecommerce_dw", alias="DW_DATABASE")
    dw_read_only: bool = Field(True, alias="DW_READ_ONLY")

    # ---------- 会话 / 业务库 (SQLite) ----------
    sqlite_path: str = Field("data/agent.db", alias="SQLITE_PATH")
    conversation_history: int = Field(10, alias="CONVERSATION_HISTORY")

    # ---------- 飞书 ----------
    feishu_app_id: str = Field("", alias="FEISHU_APP_ID")
    feishu_app_secret: str = Field("", alias="FEISHU_APP_SECRET")
    feishu_ws_enabled: bool = Field(False, alias="FEISHU_WS_ENABLED")
    # 监控看板多维表格
    bitable_app_token: str = Field("", alias="BITABLE_APP_TOKEN")
    bitable_table_id: str = Field("", alias="BITABLE_TABLE_ID")

    # ---------- 向量 / 全文检索 ----------
    milvus_uri: str = Field("http://localhost:19530", alias="MILVUS_URI")
    es_host: str = Field("http://localhost:9200", alias="ES_HOST")

    # ---------- 安全 ----------
    guardrails_enabled: bool = Field(True, alias="GUARDRAILS_ENABLED")
    max_input_chars: int = Field(2000, alias="MAX_INPUT_CHARS")
    message_aes_key: str = Field("", alias="MESSAGE_AES_KEY")

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def is_mock(self) -> bool:
        return self.llm_mode == "mock" or self.dw_mode == "mock"


@lru_cache
def get_settings() -> Settings:
    """进程级单例。测试中可通过覆盖环境变量后调用。"""
    return Settings()


settings = get_settings()
