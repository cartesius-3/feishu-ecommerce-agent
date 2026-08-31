# 飞书 AI 电商数据助手 Agent

飞书群里 @机器人 用自然语言问电商数据（"华东区上个月毛利率超过40%的SKU有哪些？"），Agent 自动识别意图 → 动态 NL2SQL 查数仓 / 调 MCP 工具 → LLM 生成分析报告 → 飞书返回结果。覆盖**商品 / 广告 / 库存预警 / 营销文案 / 文件分析 / 即席数据问答**六大电商场景。

**本仓库为公开版**：完整代码 + 架构/业务文档。外部服务（数仓/向量库/LLM/飞书）全部支持 mock 模式，**零 API Key、离线可跑通全链路**。生产对接（店小秘/领星 ERP、真实数仓）代码以适配器占位，见 [技术文档](docs/技术文档_飞书AI电商数据助手Agent.md)。

---

## 核心能力

| 场景 | 说明 | 链路 |
|------|------|------|
| 📊 即席查数 | "华东区毛利率>40%的SKU" → NL2SQL 12 节点管线 | 意图 → 三路召回 → 生成 SQL → EXPLAIN → 执行 |
| 📦 商品分析 | SKU 维度销量/库存 | product_skill → MCP 工具 → LLM 报告 |
| 📈 广告分析 | 渠道 ROI/ROAS（口径：销售额÷广告费） | ads_skill → MCP 工具 → LLM 报告 |
| ✍️ 文案生成 | 小红书/抖音/美团 5 平台模板文案 | content_skill |
| 📄 文件分析 | 上传 Excel/PDF/Word → 解析出报告 | file_parser → file_analysis_skill |
| 🚨 库存预警 | 低于阈值自动飞书群告警 + 多维表格看板 | APScheduler 定时扫描 + send_alert |

## 架构

```
飞书群/私聊 @Agent
   │  WebSocket 长连接（独立子进程，无需公网 IP）
   ▼
LangGraph 状态机（条件路由）
   START → load_history → load_file → intent_router ──条件边──▶
     data_query → NL2SQL 12 节点管线（三路召回→合并→生成→EXPLAIN→修正→执行）
     product/ads/content/file/help → 对应 skill
   → answer → save_history → END
   │
   ├─ MCP 工具层：get_inventory / get_sales_velocity / get_order_status / send_alert
   │    适配器：Mock → 店小秘 → 领星（切换 ERP 只改配置）
   ├─ 数据层：MySQL 数仓（只读账号）+ Milvus 向量 + ES 全文 + SQLite 业务库
   └─ 监控：MonitoringStats → 飞书多维表格看板（每小时）
```

完整图见 [系统架构图](docs/飞书AI电商数据Agent-系统架构图.md)、[业务流程图](docs/飞书AI电商数据Agent-业务流程图.md)。

## 快速启动（mock 模式，无需任何 Key）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动 API（默认 LLM_MODE=mock / DW_MODE=mock）
python -m app.main
# → http://localhost:8000/api/health

# 3. 命令行体验 Agent
python -m app.demo
```

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_input": "华东区毛利率超过40%的SKU有哪些？", "conversation_id": "demo"}'
```

## 目录结构

```
feishu-ecommerce-agent/
├── app/
│   ├── main.py                 # FastAPI 入口 + 飞书 WS 子进程 + 定时任务
│   ├── config.py               # 配置（环境变量 → Pydantic，mock 优先）
│   ├── prompts.py              # 全部 System Prompt
│   ├── agent/                  # LangGraph 核心
│   │   ├── state.py            # AgentState（含 NL2SQL 字段）
│   │   ├── intent_router.py    # LLM 意图识别
│   │   ├── workflow.py         # 条件边图（意图分发 + SQL 校验分支）
│   │   └── nodes/              # 12 节点（三路召回/合并/生成/校验/修正/执行）
│   ├── skills/                 # product / ads / content / file / help
│   ├── mcp/                    # 工具层：server + tools + adapters（Mock/店小秘/领星）
│   ├── tools/                  # feishu_ws / feishu_tool / file_parser / guardrails / database_tool
│   ├── core/                   # safety（五层安全）/ cost（预算缓存）/ llm / embedder
│   ├── models/                 # SQLAlchemy ORM + meta_knowledge 元数据知识库
│   ├── repositories/           # mysql 数仓 / milvus 向量 / es 全文
│   ├── rag/                    # 知识文档 RAG
│   ├── memory/                 # 会话历史（SQLite）
│   └── monitoring/             # MonitoringStats + 飞书看板同步
├── docker/                     # MySQL + Milvus + ES + TEI 一键编排（生产模式）
├── scripts/                    # init_db / build_meta_knowledge
├── docs/                       # 技术文档 / 业务文档 / 工具场景 / 架构图 / 流程图
└── requirements.txt
```

## 设计要点（面试高频）

- **为什么条件边 + LLM 路由结合**：业务规则用条件边（确定性判断），语义理解用 LLM 路由（意图识别）。命门：**判断在节点、选路在边**——节点里 LLM 把结果写进 state，条件边只读 state 分发，不重新判断。
- **NL2SQL 为什么自建不直接用 LangChain SQL Agent**：整库 Schema 扔给 LLM 硬猜准确率 <60%；自建 = 先检索定位字段/取值（向量管语义、ES 管字面），再压缩上下文，再生成，再 EXPLAIN 校验修正——准确率提到 85%（200+ 回归集）。
- **MCP 解耦**：Agent 图只引用 `get_inventory(sku_id, platform)` 稳定签名，切换 ERP（店小秘/领星）只改适配器配置。
- **五层安全**：Prompt 约束 → 正则黑名单 → SQLGlot AST → EXPLAIN 真实校验 → 只读账号兜底。

## 生产接入（非 mock）

| 项 | 配置 | 说明 |
|----|------|------|
| 数仓 | `DW_MODE=mysql` + docker/ 编排 | MySQL 8，建只读账号 |
| 向量/全文 | `EMBED_MODE=tei` / milvus / es | docker compose 一键起 |
| LLM | `LLM_MODE=deepseek` + Key | OpenAI 兼容协议 |
| 飞书 | `FEISHU_APP_ID/SECRET` + `FEISHU_WS_ENABLED=true` | WS 长连接 + 多维表格看板 |
| ERP | `MCP_ADAPTER=dianxiaomi/lingxing` | 适配器需补真实 API 实现 |

## License

MIT License
