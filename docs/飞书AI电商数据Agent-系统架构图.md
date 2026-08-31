# 飞书 AI 电商数据 Agent — 系统架构图

> 基于「飞书 AI 电商数据 Agent」项目实际架构绘制。Mermaid 兼容版，可在 VS Code / GitHub / Mermaid Live Editor 中直接渲染。

```mermaid
graph TD
    %% styles
    classDef userLayer fill:#e1f5fe,stroke:#0288d1,stroke-width:2px
    classDef gatewayLayer fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef guardLayer fill:#fce4ec,stroke:#d81b60,stroke-width:2px
    classDef agentLayer fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    classDef nl2sqlLayer fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef guardInner fill:#ffcdd2,stroke:#d81b60,stroke-width:1px
    classDef mcpLayer fill:#e0f7fa,stroke:#00838f,stroke-width:2px
    classDef ragLayer fill:#fff8e1,stroke:#f9a825,stroke-width:2px
    classDef dataLayer fill:#eceff1,stroke:#546e7a,stroke-width:2px
    classDef monitorLayer fill:#fbe9e7,stroke:#e64a19,stroke-width:2px
    classDef infraLayer fill:#e8eaf6,stroke:#3949ab,stroke-width:2px

    %% nodes: user entry
    FEISHU_APP["飞书群 @机器人<br/>自然语言提问"]
    CARD["飞书 Interactive Card<br/>流式渲染结果"]

    %% nodes: gateway
    WS["feishu_ws.py 独立子进程<br/>WebSocket 长连接<br/>无需公网 IP"]

    %% nodes: guard
    SENSITIVE["敏感词过滤"]
    TOPIC_CHECK["非电商话题识别"]

    %% nodes: agent orchestration
    INTENT["意图识别 Router"]
    GOODS["商品分析 Skill"]
    AD_SKILL["广告分析 Skill"]
    INVENTORY["库存预警 Skill"]
    NL2SQL_ENTRY["NL2SQL 即席查询 Skill"]
    MARKETING["营销文案 Skill"]
    FILE_ANALYSIS["文件分析 Skill"]
    CHECKPOINT["Checkpointer<br/>对话状态持久化"]
    HUMAN_LOOP["interrupt 人机协同"]

    %% nodes: NL2SQL pipeline
    JIEBA["1. jieba 分词<br/>关键词提取"]
    MILVUS_R["2. Milvus 向量检索<br/>字段名/指标匹配<br/>例:毛利率->profit_margin"]
    ES_R["2. ES 全文检索<br/>维度取值匹配<br/>例:华东区->region_name"]
    LLM_SELECT["3. LLM 筛选<br/>相关表和字段"]
    SQL_GEN["4. LLM 动态 SQL 生成"]
    L1["5. 防线1:Prompt约束<br/>只能SELECT"]
    L2["6. 防线2:正则扫描<br/>拦截DROP/DELETE/INSERT"]
    L3["7. 防线3:SQLGlot AST<br/>校验根节点=SELECT"]
    L4["8. 防线4:EXPLAIN验证<br/>抓表名/字段错误"]
    L5["9. 防线5:只读账号<br/>执行SELECT"]
    AUTO_FIX["自动修正<br/>EXPLAIN失败->回注Prompt<br/>LLM重生成 修正率~85%"]

    %% nodes: MCP tools
    MCP_TOOLS["四组标准化工具<br/>get_inventory / get_sales<br/>get_orders / send_alert"]
    ADAPTER["适配器模式路由器"]
    MOCK["Mock 演示"]
    DXMI["店小秘 API"]
    LX["领星 API 扩展"]
    AMZ["Amazon SP-API 扩展"]

    %% nodes: RAG
    DOC_PARSE["文档解析<br/>MinerU/PyMuPDF/PaddleOCR"]
    CHUNK["智能分块"]
    DUAL_RECALL["BM25+向量双路召回"]
    RRF_FUSE["RRF 融合排序"]
    RERANK["Cross-Encoder Rerank<br/>精排+低分拦截"]

    %% nodes: data
    PG["MySQL<br/>数仓+元数据 只读账号"]
    REDIS["Redis<br/>对话缓存10条+双写"]
    MILVUS_DB["Milvus<br/>向量数据库"]
    ES_DB["Elasticsearch<br/>全文索引"]
    RABBITMQ["RabbitMQ<br/>消息队列"]

    %% nodes: monitor
    STATS["MonitoringStats 自研<br/>LLM调用/Skill耗时/错误数"]
    SCHEDULER["APScheduler<br/>每小时推送到飞书"]
    FEISHU_TABLE["飞书多维表格<br/>监控看板"]
    TIMEOUT["LLM 30s 超时兜底"]
    CACHE["对话历史缓存<br/>内存10条+DB双写"]

    %% nodes: infra
    FASTAPI["FastAPI 主服务"]
    DOCKER["Docker 容器化"]

    %% edges
    FEISHU_APP -->|"WebSocket"| WS
    WS --> SENSITIVE
    SENSITIVE --> TOPIC_CHECK
    TOPIC_CHECK -->|"通过"| INTENT
    TOPIC_CHECK -.->|"拦截"| WS

    INTENT -->|"商品"| GOODS
    INTENT -->|"广告"| AD_SKILL
    INTENT -->|"库存"| INVENTORY
    INTENT -->|"复杂查询"| NL2SQL_ENTRY
    INTENT -->|"文案"| MARKETING
    INTENT -->|"文件"| FILE_ANALYSIS

    INTENT --> CHECKPOINT
    CHECKPOINT --> REDIS
    CHECKPOINT --> PG

    NL2SQL_ENTRY --> JIEBA
    JIEBA --> MILVUS_R
    JIEBA --> ES_R
    MILVUS_R --> LLM_SELECT
    ES_R --> LLM_SELECT
    LLM_SELECT --> SQL_GEN
    SQL_GEN --> L1
    L1 --> L2
    L2 --> L3
    L3 --> L4
    L4 --> L5
    L4 -.->|"失败"| AUTO_FIX
    AUTO_FIX -->|"修正后重试"| SQL_GEN
    L5 -->|"执行SQL"| PG

    GOODS --> MCP_TOOLS
    AD_SKILL --> MCP_TOOLS
    INVENTORY --> MCP_TOOLS
    MARKETING --> MCP_TOOLS
    MCP_TOOLS --> ADAPTER
    ADAPTER --> MOCK
    ADAPTER --> DXMI
    ADAPTER -.->|"可扩展"| LX
    ADAPTER -.->|"可扩展"| AMZ

    FILE_ANALYSIS --> DOC_PARSE
    DOC_PARSE --> CHUNK
    CHUNK --> DUAL_RECALL
    DUAL_RECALL --> RRF_FUSE
    RRF_FUSE --> RERANK
    DUAL_RECALL --> MILVUS_DB
    DUAL_RECALL --> ES_DB

    GOODS --> CARD
    AD_SKILL --> CARD
    INVENTORY --> CARD
    NL2SQL_ENTRY --> CARD
    MARKETING --> CARD
    FILE_ANALYSIS --> CARD
    CARD -.->|"流式推送"| FEISHU_APP

    INTENT --> STATS
    STATS --> SCHEDULER
    SCHEDULER --> FEISHU_TABLE
    INTENT --> TIMEOUT

    WS --> FASTAPI
    FASTAPI --> INTENT

    %% class assignments (Mermaid 8.x compatible)
    class FEISHU_APP,CARD userLayer
    class WS gatewayLayer
    class SENSITIVE,TOPIC_CHECK guardLayer
    class INTENT,GOODS,AD_SKILL,INVENTORY,NL2SQL_ENTRY,MARKETING,FILE_ANALYSIS,CHECKPOINT,HUMAN_LOOP agentLayer
    class JIEBA,MILVUS_R,ES_R,LLM_SELECT,SQL_GEN,AUTO_FIX nl2sqlLayer
    class L1,L2,L3,L4,L5 guardInner
    class MCP_TOOLS,ADAPTER,MOCK,DXMI,LX,AMZ mcpLayer
    class DOC_PARSE,CHUNK,DUAL_RECALL,RRF_FUSE,RERANK ragLayer
    class PG,REDIS,MILVUS_DB,ES_DB,RABBITMQ dataLayer
    class STATS,SCHEDULER,FEISHU_TABLE,TIMEOUT,CACHE monitorLayer
    class FASTAPI,DOCKER infraLayer
```

## 架构分层速查

| 层级 | 颜色 | 核心组件 | 关键技术 |
|------|------|----------|----------|
| 🔵 用户入口 | 浅蓝 | 飞书群 @机器人 + Interactive Card | 流式渲染，唯一入口 |
| 🟠 网关层 | 浅橙 | feishu_ws.py | WebSocket 独立子进程，无需公网 IP |
| 🔴 安检层 | 浅粉 | Guardrails | 敏感词 + 非电商话题过滤 |
| 🟢 Agent 编排 | 浅绿 | LangGraph StateGraph | 条件边路由 / Checkpointer / interrupt |
| 🟣 NL2SQL | 浅紫 | jieba + Milvus + ES + SQLGlot | 双路检索 + 五道安全防线 + 自动修正 |
| 🔵 MCP 工具 | 浅青 | 适配器模式 | 标准接口 get_inventory/get_sales/get_orders/send_alert |
| 🟡 RAG 检索 | 浅黄 | MinerU + BM25 + Cross-Encoder | 双路召回 + RRF 融合 + 精排拦截 |
| ⬜ 数据层 | 灰 | MySQL / Redis / Milvus / ES | 混合存储（数仓+对话缓存+向量+全文），只读账号兜底 |
| 🟤 监控容错 | 浅棕 | MonitoringStats 自研 | APScheduler -> 飞书多维表格看板 |
| 🔵 基础设施 | 靛蓝 | FastAPI + Docker | 主服务 + 容器化 |
