# 飞书AI电商数据助手Agent — 业务文档

> 基础项目：Agent_feishu (KDHR9100, MIT License)  
> 核心升级：动态NL2SQL + MCP工具层 + LangGraph条件路由 + 飞书多维表格监控看板

---

## 一、项目一句话描述

飞书群里 @机器人 用自然语言问电商数据（"SKU001最近一周卖了多少？""哪个广告ROI最高？""毛利率>40%且库存低于安全线的SKU有哪些？"），Agent自动识别意图 → 动态NL2SQL查数据库/调MCP工具 → LLM生成分析报告 → 飞书返回结果。覆盖商品分析、广告分析、库存预警、营销文案、文件分析、即席数据问答六大电商场景。

## 二、解决的业务问题

| 业务场景 | 以前怎么做 | 现在怎么做 |
|---------|-----------|-----------|
| 运营查SKU销量 | 登ERP→搜SKU→看报表→自己算趋势 | @机器人 "SKU001最近一周销量" → 自动返回趋势分析+建议 |
| 投放查广告ROI | 登各个广告平台→导出数据→Excel汇总 | @机器人 "哪个渠道ROI最高" → 自动聚合分析 |
| 库存预警 | 每天人工巡检→Excel标红 | Agent定时扫描+低于阈值飞书群自动告警+多维表格看板 |
| 营销文案 | 运营自己写→反复改 | @机器人 "写个抖音带货文案" → 多平台模板生成 |
| 表格数据分析 | 下载Excel→人工分析→写报告 | 飞书上发Excel文件→Agent解析→自动生成分析报告 |
| 即席数据问答 | 找数据分析师写SQL | @机器人 任意问题→动态NL2SQL→自动返回结果 |

## 三、核心业务Skill

### 3.1 product_skill — 商品销售分析

用户输入 → 正则提取SKU（或走NL2SQL管线处理非预设问题）→ 查数据库 → 计算趋势（上涨/下跌/平稳）→ 计算利润率 → LLM生成分析报告 → 返回

**示例对话**：
- "SKU001最近一周卖了多少？" → 返回销量趋势 + 利润率 + 优化建议
- "哪个品类卖得最好？" → 返回品类排行 + 销售额占比
- "华东区上个月毛利率超过40%的SKU有哪些？" → NL2SQL动态生成查询 → 返回结果列表

### 3.2 ads_skill — 广告投放分析

用户输入 → 正则提取广告ID（或走NL2SQL管线）→ 查广告数据 → 按平台聚合 → 计算ROI/ROAS/CPA → LLM生成分析报告 → 返回

**示例对话**：
- "哪个渠道ROI最高？" → 返回平台对比 + ROI排行 + 优化建议
- "AD001广告最近表现怎么样？" → 返回点击/转化趋势 + 成本分析

### 3.3 content_skill — 营销文案生成

用户输入 → 检测平台（抖音/淘宝/小红书/微信/拼多多）→ 检测模板类型 → 提取产品信息 → LLM生成文案 → 返回

**示例对话**：
- "写个抖音带货文案，产品是防晒霜，卖点是清爽不油腻" → 返回抖音风格带货文案
- "小红书上怎么介绍这款面膜？" → 返回小红书风格种草文案

### 3.4 file_analysis_skill — 文件数据分析

飞书用户发Excel/CSV/PDF/Word文件 → 下载 → 解析 → 提取列名/行数/统计摘要/样本 → LLM生成分析报告 → 返回

**示例对话**：
- [上传本月销售数据.xlsx] "帮我分析一下这个月的趋势" → 返回数据概览 + 关键指标 + 趋势分析

### 3.5 help_skill — 帮助引导

用户问"你能做什么" → 回复六大能力介绍（商品分析/广告分析/库存预警/营销文案/文件分析/即席数据查询）

## 四、数据模型

```
product_sales          — 商品销售表
  ├─ sku, product_name, category
  ├─ sales_volume, revenue, cost, inventory, avg_price
  └─ date, source

ads_performance        — 广告投放表
  ├─ ad_id, ad_name, platform, campaign_id, ad_group_id
  ├─ clicks, impressions, spend, conversions, conversion_value
  └─ ctr, cpc, roas, date

conversations          — 对话记录表
  ├─ conversation_id, user_id, user_name
  ├─ role, content, intent, skill
  └─ token_usage(JSON), response_time_ms, created_at

user_profiles          — 用户画像表
  ├─ user_id, user_name, department, role
  ├─ preferences(JSON), interaction_count
  └─ last_interaction, created_at, updated_at

meta_tables            — NL2SQL元数据知识库
  ├─ table_name, column_name, column_type, business_meaning
  ├─ is_dimension, is_metric, related_columns
  └─ examples, description
```

## 五、核心技术特性（已完成升级）

| 特性 | 实现方式 |
|------|---------|
| **动态NL2SQL** | 元数据知识库 + jieba关键词提取 → Milvus向量检索字段/指标 + ES全文检索取值 → 三路并行召回合并 → LLM过滤无关表 → 动态生成SQL → SQLGlot语法解析 + EXPLAIN真实校验 → 失败自动LLM修正 |
| **LangGraph条件路由** | SQL校验通过→执行节点；校验失败→LLM修正节点→再执行。库存低于阈值→告警节点；库存正常→直接返回。确定性业务规则用条件边，语义判断用LLM路由 |
| **MCP工具抽象** | FastMCP封装库存查询/销售分析/订单追踪/告警推送四组工具。工具签名稳定（如get_inventory(sku_id, platform)），底层适配器可替换（店小秘→领星→直连Amazon SP-API），Agent路由逻辑不感知 |
| **飞书多维表格监控看板** | 定时同步关键指标（LLM调用次数/Token消耗/各Skill耗时分布/错误率/日活用户）到飞书多维表格，团队可实时查看Agent运行状态 |
| **SQL安全五层防护** | Prompt约束→正则黑名单→SQLGlot语法解析→EXPLAIN真实校验→只读数据库账号 |
| **混合模型路由** | 简单意图+SQL生成用DeepSeek（成本低效果够），复杂分析用GPT-4o（贵但必要），日Token预算管控 |

## 六、技术栈一览

| 层 | 技术 | 用途 |
|----|------|------|
| Agent框架 | LangGraph 1.2.9 | 状态机构建 + 条件路由 + 节点编排 |
| LLM调用 | LangChain 1.3.14 + ChatOpenAI | LLM统一接口（DashScope兼容模式） |
| 默认模型 | DeepSeek V4 Pro / GPT-4o | 意图路由 + SQL生成 + 分析报告 |
| MCP协议 | FastMCP (Python) | 工具标准化封装，Agent与实现解耦 |
| NL2SQL | jieba + Milvus + Elasticsearch | 关键词提取 + 向量/全文混合检索 + SQL生成校验 |
| 向量库 | Milvus + FAISS (RAG) | 混合向量检索。Milvus中国生态强、分布式免费、字节/小米/快手等大厂在用，适合十亿级向量 |
| 全文检索 | Elasticsearch | 字段取值精确匹配 |
| Embedding | BGE-large-zh-v1.5 + MiniLM | 远程主用 + 本地RAG |
| Web框架 | FastAPI 0.139 | HTTP API + 健康检查 |
| 飞书SDK | lark-oapi 1.7.1 | WebSocket长连接 + REST API + 多维表格 |
| 数据库 | SQLite + SQLAlchemy 2.0 + MySQL(数仓) | 业务数据 + 对话记录 + 数仓查询 |
| 文件解析 | openpyxl + PyPDF2 + python-docx | Excel/PDF/Word解析 |
| 安全 | Guardrails + SQLGlot + AES | 输入过滤 + SQL校验 + 消息解密 |
| 监控 | MonitoringStats + 飞书多维表格 | 全链路追踪 + Token计费 + 看板展示 |
