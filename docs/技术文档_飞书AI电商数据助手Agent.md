# 飞书AI电商数据助手Agent — 技术文档

---

## 一、系统架构全景

```
┌──────────────────────────────────────────────────────────────────┐
│                         飞书群 / 私聊                              │
│              @Ecommerce Agent "华东区毛利率>40%的SKU有哪些"         │
└─────────────────────────────┬────────────────────────────────────┘
                              │ WebSocket 长连接
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  feishu_ws.py (独立子进程)                                        │
│  ├─ lark_oapi WSClient 接收消息                                   │
│  ├─ @提及检测 + 群聊/私聊判断                                      │
│  ├─ 文件下载 + 解析 (Excel/CSV/PDF/Word → 结构化文本)              │
│  └─ message_queue → process_messages() 线程                       │
└─────────────────────────────┬────────────────────────────────────┘
                              │ agent.invoke()
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  LangGraph 状态机 (app/agent/workflow.py)                         │
│                                                                    │
│  START → load_history → load_file → intent_router                 │
│                                          │                        │
│              ┌───────────────────────────┼───────────────┐       │
│              ▼                           ▼               ▼       │
│      data_query (NL2SQL)         product_skill     content_skill  │
│              │                           │               │       │
│     extract_keywords                     │               │       │
│           │                              │               │       │
│  ┌────────┼────────┐                     │               │       │
│  ▼        ▼        ▼                     │               │       │
│ recall   recall   recall                 │               │       │
│ column   value    metric                 │               │       │
│  └────────┼────────┘                     │               │       │
│           ▼                              │               │       │
│   merge + filter + generate_sql          │               │       │
│           │                              │               │       │
│           ▼                              │               │       │
│      validate_sql                        │               │       │
│        ┌───┴───┐                         │               │       │
│    error=None error≠None                 │               │       │
│        │         │                       │               │       │
│        ▼         ▼                       │               │       │
│    run_sql  correct_sql→run_sql          │               │       │
│        │         │                       │               │       │
│        └────┬────┘                       │               │       │
│             ▼                            │               │       │
│          answer ←────────────────────────┘               │       │
│             │                                            │       │
│             ▼                                            │       │
│        save_history                                      │       │
│             │                                            │       │
│             ▼                                            │       │
│           END                                             │       │
│                                                            │       │
│  ┌──────────────────────────────────────────────────────┐ │       │
│  │ MCP Tool Layer (FastMCP)                              │ │       │
│  │ get_inventory / get_sales_velocity / get_order_status │ │       │
│  │ send_alert / query_dw                                 │ │       │
│  │ 适配器: Mock → 店小秘API → 领星API → Amazon SP-API    │ │       │
│  └──────────────────────────────────────────────────────┘ │       │
│  ┌──────────────────────────────────────────────────────┐ │       │
│  │ 数据层                                                │ │       │
│  │ Milvus(向量) + Elasticsearch(全文) + MySQL(数仓+元数据)│ │       │
│  └──────────────────────────────────────────────────────┘ │       │
└──────────────────────────────────────────────────────────────────┘
```

## 二、LangGraph 工作流详解

### 2.1 AgentState（共享状态）

```python
class AgentState(TypedDict, total=False):
    user_input: str                # 用户输入文本
    conversation_id: str           # 会话ID（飞书chat_id）
    history: List[Dict]            # 最近10条对话历史
    tool_result: dict              # 路由结果 + Skill/NL2SQL执行结果
    answer: str                    # 最终回复文本
    intent: str                    # 识别到的意图 (data_query/product/ads/content/file/help)
    token_usage: Dict[str, int]    # Token消耗统计
    file_path: str                 # 上传文件路径
    file_content: str              # 解析后的文件内容
    # NL2SQL专用字段
    keywords: List[str]            # jieba提取的关键词
    retrieved_columns: List[dict]  # Milvus召回的字段信息
    retrieved_values: List[dict]   # ES召回的取值信息
    retrieved_metrics: List[dict]  # Milvus召回的指标信息
    generated_sql: str             # LLM生成的SQL
    sql_error: str                 # EXPLAIN校验错误信息
    query_result: List[dict]       # SQL执行结果
```

### 2.2 节点详解

#### 通用节点（所有意图共用）

| 节点 | 函数 | 做什么 |
|------|------|--------|
| load_history | load_history(state) | 从LocalMemory加载最近10条对话历史 |
| load_file | load_file(state) | 若有上传文件，调FileParserTool解析并格式化摘要 |
| intent_router | intent_router(state) | LLM+StructuredTool识别意图：data_query / product / ads / content / file / help |

#### NL2SQL管线节点（意图=data_query时进入）

| 节点 | 函数 | 做什么 |
|------|------|--------|
| extract_keywords | extract_keywords(state) | jieba TF-IDF提取关键词，保留原始query |
| recall_column | recall_column(state) | Milvus向量检索字段——Embedding→语义匹配列名 |
| recall_value | recall_value(state) | ES全文检索取值——精确匹配"华东区"等维度值 |
| recall_metric | recall_metric(state) | Milvus向量检索指标——语义匹配"毛利率"等指标定义 |
| merge_retrieved | merge_retrieved_info(state) | 三路合并去重 + 补全主外键 + 回填示例值 |
| filter_schema | filter_table_and_metric(state) | LLM并行过滤无关表和指标，减少SQL生成token |
| add_context | add_extra_context(state) | 补齐当前日期/weekday/quarter + DB dialect/version |
| generate_sql | generate_sql(state) | Prompt + 结构化上下文 → LLM → 纯SQL文本 |
| validate_sql | validate_sql(state) | EXPLAIN <sql> 在真实DW上校验 |
| correct_sql | correct_sql(state) | LLM根据error信息修正SQL |
| run_sql | run_sql(state) | 执行SQL → 流式推送结果 |
| answer | answer_node(state) | LLM将查询结果格式化为自然语言 + 飞书卡片渲染 |
| save_history | save_history(state) | 持久化对话记录到SQLite |

#### 业务Skill节点（意图非data_query时进入）

| 节点 | 做什么 |
|------|--------|
| product_skill | 正则提取SKU → 调MCP工具 get_sales_velocity() → LLM分析报告 |
| ads_skill | 正则提取广告ID → 调MCP工具 → 计算ROI/ROAS → LLM分析报告 |
| content_skill | 检测平台+模板 → LLM生成文案 |
| file_analysis_skill | 文件已解析 → LLM生成分析报告 |
| help_skill | LLM + HELP_PROMPT → 回复能力介绍 |

### 2.3 条件边设计（核心升级）

```
intent_router
  ├── intent="data_query"     → extract_keywords (进入NL2SQL管线)
  ├── intent="product"        → product_skill
  ├── intent="ads"            → ads_skill
  ├── intent="content"        → content_skill
  ├── intent="file"           → file_analysis_skill
  └── intent="help/unknown"   → help_skill

validate_sql
  ├── error=None              → run_sql (条件边：SQL语法正确，直接执行)
  └── error≠None              → correct_sql → run_sql (条件边：校验失败，LLM修正后执行)
```

**设计原则**：
- 意图路由：LLM判断（语义问题）→ 走 LangGraph 条件边分发到不同子图
- SQL校验：EXPLAIN结果确定性判断（成功/失败）→ 走条件边分支
- 库存预警、异常检测等阈值判断也走条件边——**业务规则用条件边，语义理解用LLM路由**

## 三、NL2SQL管线详解（12节点）

> **不是 LangChain 自带的 SQL Agent。** LangChain 的 `SQLDatabaseChain` / `create_sql_agent` 做法是把整个数据库 Schema 一次性扔给 LLM 让它直接写 SQL——没有检索、没有过滤、没有校验。电商几百个字段的场景下，LLM 根本不知道用户说的"毛利率"对应哪列、"华东区"是哪个维度值，准确率不到 60%。本项目的 NL2SQL 管线完全自建：先检索定位字段和取值、再过滤压缩上下文、再生成 SQL、再双重校验修正。LangChain 只用于节点内调用 LLM，Schema 管理、检索、校验全部自己实现。

### 3.1 关键词提取

```python
# jieba TF-IDF + 词性过滤
keywords = jieba.analyse.extract_tags(
    query, topK=10,
    allowPOS=('n','nr','ns','nt','nz','v','vn','a','an','eng')
)
# 保留原始query + 去重
keywords = list(set(keywords + [query]))
```

### 3.2 三路并行召回

```
query = "华东区上个月毛利率超过40%的SKU有哪些？"

[recall_column]  Milvus向量检索
  "毛利率" → Embedding → 找到 fact_order.profit_margin, fact_order.gross_profit_rate
  "SKU"    → Embedding → 找到 dim_product.sku_code

[recall_value]   ES全文检索
  "华东区" → BM25精确匹配 → dim_region.region_name = '华东'

[recall_metric]  Milvus向量检索
  "毛利率" → Embedding → 找到 metric: gross_margin (公式: (revenue-cost)/revenue*100)
```

**为什么三路分开**：
- 字段检索（Milvus向量）：语义匹配，如"销售额"→gmv列——向量最擅长
- 取值检索（ES全文）：精确匹配，如"华东区"→'华东'——"华东"和"华北"向量太近，向量容易混淆
- 指标检索（Milvus向量）：语义匹配指标定义和计算公式

### 3.3 合并与过滤

```python
# merge_retrieved_info
merged_table_infos = merge_by_column_id(columns)       # 去重
merged_table_infos = fill_metric_columns(metrics)      # 补全指标依赖字段
merged_table_infos = fill_value_examples(values)        # 回填示例值到columns
merged_table_infos = fill_foreign_keys(tables)          # 补齐JOIN条件

# filter_table + filter_metric (两个LLM节点并行)
filtered_tables = llm.filter(YAML_input, query)         # 从候选集中筛选
filtered_metrics = llm.filter(YAML_input, query)
```

### 3.4 SQL生成与校验

```python
# generate_sql — Prompt模板 + 结构化上下文
prompt = GENERATE_SQL_PROMPT.format(
    tables_yaml=filtered_tables,
    metrics_yaml=filtered_metrics,
    date_info=date_info,
    db_info=db_info,
    query=query
)
sql = llm.invoke(prompt, temperature=0)  # Temperature=0确保确定性

# validate_sql — EXPLAIN真实校验
try:
    await db.execute(text(f"EXPLAIN {sql}"))
    state["sql_error"] = None  # 通过，走run_sql
except Exception as e:
    state["sql_error"] = str(e)  # 失败，走correct_sql
```

### 3.5 NL2SQL安全五层防护

| 层 | 方法 | 代码位置 | 说明 |
|----|------|---------|------|
| 1 | Prompt约束 | generate_sql.prompt | "只能生成SELECT，禁止INSERT/UPDATE/DELETE/DROP/CREATE" |
| 2 | 正则黑名单 | core/safety.py | POST-PROCESS过滤 `\bDROP\b|\bDELETE\b|\bINSERT\b` 等 |
| 3 | SQLGlot语法解析 | core/safety.py | `sqlglot.parse_one(sql).key == "select"` 校验 |
| 4 | EXPLAIN真实校验 | validate_sql节点 | 在DW上执行EXPLAIN，发现表不存在/列名错误等问题 |
| 5 | 只读数据库账号 | config/dw.py | DW连接使用READ ONLY权限MySQL用户 |

## 四、MCP工具层设计

```python
# mcp/server.py — FastMCP Server
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ecommerce-tools")

# ========== 库存工具 ==========
@mcp.tool()
async def get_inventory(sku_id: str, platform: str = None) -> dict:
    """查询指定SKU在各平台的实时库存。
    底层适配器: MockInventory → DianxiaomiInventory → LingxingInventory
    """
    adapter = get_current_adapter()
    return await adapter.get_inventory(sku_id, platform)

@mcp.tool()
async def get_low_stock_skus(threshold: int = 10) -> list[dict]:
    """查询库存低于阈值的所有SKU"""
    ...

# ========== 销售工具 ==========
@mcp.tool()
async def get_sales_velocity(sku_id: str, days: int = 7) -> dict:
    """查询SKU近N天的日均销量和趋势"""
    ...

@mcp.tool()
async def get_sales_by_region(region: str, date_range: str) -> dict:
    """按区域统计销售额"""
    ...

# ========== 订单工具 ==========
@mcp.tool()
async def get_order_status(order_id: str) -> dict:
    """查询订单当前状态（待发货/运输中/已签收/退款中）"""
    ...

# ========== 通知工具 ==========
@mcp.tool()
async def send_alert(chat_id: str, title: str, message: str, level: str = "info"):
    """向飞书群发送告警消息 + 写入多维表格告警记录"""
    ...

# ========== 适配器模式 ==========
class InventoryTool(Protocol):
    async def get_inventory(self, sku_id: str, platform: str) -> dict: ...

class MockInventory(InventoryTool):       # 内存实现（演示用）
    ...

class DianxiaomiInventory(InventoryTool): # 店小秘OpenAPI
    ...

class LingxingInventory(InventoryTool):   # 领星API
    ...
```

**MCP的核心价值**：工具签名稳定，Agent图里引用的是 `get_inventory(sku_id, platform)` 这个接口。切换ERP只需要改一行适配器配置，不需要改Agent图任何节点和边。这就是工具与Agent解耦。

## 五、飞书集成架构

```
app/main.py (FastAPI 主进程)
  │
  │  startup_event:
  │    subprocess.Popen([sys.executable, "-m", "app.tools.feishu_ws", ...])
  │
  ▼
app/tools/feishu_ws.py (独立子进程)
  │
  ├─ lark_oapi WSClient → WebSocket长连接（无需公网IP）
  ├─ 事件注册: p2_im_message_receive_v1
  ├─ message_queue: queue.Queue()
  ├─ process_messages() 守护线程
  │   ├─ @提及检测（群聊必须@才响应）
  │   ├─ 文件下载 + 解析 (FileParserTool)
  │   ├─ guardrails.check_input() 安全检测
  │   └─ agent.invoke() → feishu_tool.reply_message()
  │
  ├─ FeishuTool (app/tools/feishu_tool.py)
  │   ├─ get_tenant_access_token() — 缓存7000秒
  │   ├─ reply_message() / send_message()
  │   ├─ download_file() — 优先IM资源API，回退Drive API
  │   ├─ get_user_info()
  │   └─ sync_to_bitable() — 🔥 同步监控数据到飞书多维表格
  │
  └─ FileParserTool (app/tools/file_parser_tool.py)
      ├─ parse_local_file() — Excel/CSV/PDF/Word
      └─ format_file_summary() — 列统计 + 样本数据
```

## 六、监控看板（飞书多维表格）

```python
# app/monitoring/dashboard.py
async def sync_metrics_to_bitable():
    """每小时同步到飞书多维表格"""
    stats = monitoring_stats.get_health_status()
    
    bitable.append_records(table_id="tblXXX", records=[{
        "时间": datetime.now(),
        "LLM调用次数": stats["llm_calls"]["count"],
        "LLM平均耗时(ms)": stats["llm_calls"]["avg_time"],
        "LLM错误数": stats["llm_calls"]["errors"],
        "飞书API调用": stats["feishu_api_calls"]["count"],
        "数据库查询": stats["database_queries"]["count"],
        "Token消耗(prompt)": stats["total_tokens"]["prompt"],
        "Token消耗(completion)": stats["total_tokens"]["completion"],
        "Product Skill耗时": stats["skill_calls"]["product"]["avg_time"],
        "Ads Skill耗时": stats["skill_calls"]["ads"]["avg_time"],
        "NL2SQL成功率": stats["skill_calls"]["data_query"]["success_rate"],
        "意图分布": json.dumps(stats["intent_counts"]),
        "错误率": stats["error_rate"],
    }])

# APScheduler 定时任务
scheduler.add_job(sync_metrics_to_bitable, 'interval', hours=1)
```

## 七、项目目录结构

```
feishu-ecommerce-agent/
├── app/
│   ├── main.py                       # FastAPI入口 + 启动飞书WS子进程
│   ├── config.py                     # 配置类 (环境变量 → Pydantic)
│   ├── prompts.py                    # 所有System Prompt模板
│   │
│   ├── agent/                        # LangGraph核心
│   │   ├── state.py                  # AgentState (TypedDict, 含NL2SQL字段)
│   │   ├── intent_router.py          # 意图路由 (LLM + StructuredTools)
│   │   ├── workflow.py               # StateGraph构建 (条件边 + 子图)
│   │   └── nodes/
│   │       ├── extract_keywords.py   # NL2SQL: jieba关键词提取
│   │       ├── recall_column.py      # NL2SQL: Milvus字段召回
│   │       ├── recall_value.py       # NL2SQL: ES取值召回
│   │       ├── recall_metric.py      # NL2SQL: Milvus指标召回
│   │       ├── merge_retrieved.py    # NL2SQL: 三路合并
│   │       ├── filter_schema.py      # NL2SQL: LLM过滤表+指标
│   │       ├── add_context.py        # NL2SQL: 日期+DB上下文
│   │       ├── generate_sql.py       # NL2SQL: LLM生成SQL
│   │       ├── validate_sql.py       # NL2SQL: EXPLAIN校验
│   │       ├── correct_sql.py        # NL2SQL: LLM修正SQL
│   │       ├── run_sql.py            # NL2SQL: 执行SQL
│   │       └── answer.py             # 通用: LLM生成自然语言回复
│   │
│   ├── skills/                       # 业务Skill
│   │   ├── product_skill.py          # 商品分析 (调MCP工具)
│   │   ├── ads_skill.py              # 广告分析 (调MCP工具)
│   │   ├── content_skill.py          # 文案生成 (5平台×5模板)
│   │   ├── file_analysis_skill.py    # 文件分析
│   │   └── help_skill.py             # 帮助引导
│   │
│   ├── mcp/                          # MCP工具层
│   │   ├── server.py                 # FastMCP Server入口
│   │   ├── tools/
│   │   │   ├── inventory_tools.py    # 库存工具
│   │   │   ├── sales_tools.py        # 销售工具
│   │   │   ├── order_tools.py        # 订单工具
│   │   │   └── alert_tools.py        # 告警工具
│   │   └── adapters/
│   │       ├── mock.py               # 模拟适配器
│   │       ├── dianxiaomi.py         # 店小秘适配器
│   │       └── lingxing.py           # 领星适配器
│   │
│   ├── tools/                        # 基础工具层
│   │   ├── database_tool.py          # SQL查询
│   │   ├── feishu_ws.py              # 飞书WebSocket
│   │   ├── feishu_tool.py            # 飞书REST API
│   │   ├── file_parser_tool.py       # 文件解析
│   │   └── guardrails.py             # 输入安全
│   │
│   ├── core/                         # 基础设施
│   │   ├── safety.py                 # NL2SQL五层安全防护
│   │   └── cost.py                   # 混合模型路由 + 缓存 + 预算
│   │
│   ├── models/                       # 数据层
│   │   ├── database.py               # SQLAlchemy Engine
│   │   ├── models.py                 # ORM (4表 + meta表)
│   │   └── meta_knowledge.py         # 元数据知识库构建
│   │
│   ├── repositories/                 # 数据仓储
│   │   ├── mysql/dw_repository.py    # 数仓查询 + EXPLAIN
│   │   ├── Milvus/                   # Milvus向量索引
│   │   └── es/                       # ES全文索引
│   │
│   ├── rag/                          # RAG知识库
│   ├── memory/local_memory.py        # 对话历史
│   └── monitoring/
│       ├── stats.py                  # MonitoringStats
│       └── dashboard.py              # 飞书多维表格同步
│
├── data/
├── docker/                           # MySQL + Milvus + ES + TEI
├── scripts/
│   ├── init_db.py
│   └── build_meta_knowledge.py       # 初始化元数据知识库
└── requirements.txt
```

## 八、技术栈完整表

| 层 | 技术 | 用途 |
|----|------|------|
| Agent框架 | LangGraph 1.2.9 | 状态机构建 + 条件路由 + 节点编排 |
| LLM调用 | LangChain 1.3.14 + ChatOpenAI | LLM统一接口（DashScope兼容模式） |
| 主模型 | DeepSeek V4 Pro | 意图路由 + SQL生成 + 分析报告 |
| 备选模型 | GPT-4o | 复杂分析兜底 |
| MCP协议 | FastMCP (Python) | 工具标准化，Agent与实现解耦 |
| 关键词提取 | jieba 0.42 | TF-IDF + 词性过滤 |
| 向量检索 | Milvus | 字段+指标语义匹配。中国生态强、分布式免费、字节/小米/快手等大厂在用，支持十亿级向量 |
| 全文检索 | Elasticsearch 8.x | BM25精确匹配取值 |
| Embedding | BGE-large-zh-v1.5 (TEI) | 远程主用 |
| Embedding(本地) | MiniLM (sentence-transformers) | RAG本地向量化 |
| Web框架 | FastAPI 0.139 | HTTP API + 健康检查 |
| 飞书SDK | lark-oapi 1.7.1 | WebSocket + REST API + 多维表格 |
| 数据库 | SQLite + MySQL | 业务数据 + 数仓 + 元数据库 |
| ORM | SQLAlchemy 2.0 (async) | 数据库抽象 |
| SQL安全 | SQLGlot | AST语法解析 + SELECT校验 |
| 文件解析 | openpyxl + PyPDF2 + python-docx | Excel/PDF/Word |
| 安全 | Guardrails + AES | 输入过滤 + 消息解密 |
| 监控 | MonitoringStats + APScheduler | 全链路追踪 + 定时同步飞书看板 |
| 调度 | APScheduler 3.11 | 定时任务（库存扫描 + 看板同步） |
| 部署 | Docker Compose | MySQL + Milvus + ES + TEI 一键启动 |
