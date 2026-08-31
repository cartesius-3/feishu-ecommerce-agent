# 飞书 AI 电商数据 Agent — 业务流程图

> 基于张云阳简历中「飞书 AI 电商数据 Agent」项目绘制。Mermaid 兼容版。

## 一、主流程：用户提问 → 飞书返回结果

```mermaid
sequenceDiagram
    participant User as 运营人员
    participant FS as 飞书群
    participant WS as WebSocket网关
    participant Guard as Guardrails
    participant Agent as LangGraph Agent
    participant NL2SQL as NL2SQL管线
    participant DB as 数据层
    participant Card as Interactive Card

    User->>FS: @机器人 提问
    FS->>WS: WebSocket 推送消息
    WS->>Guard: 原始消息

    Guard->>Guard: 敏感词过滤 + 话题识别

    alt 命中敏感词或非电商话题
        Guard-->>WS: 拦截
        WS-->>FS: 友好提示
    else 通过安检
        Guard->>Agent: 清洗后消息 + 用户上下文
        Note over Agent: 意图识别 → 路由到 NL2SQL
        Agent->>NL2SQL: 进入 NL2SQL 即席查询

        Note over NL2SQL: 阶段1 元数据检索
        NL2SQL->>NL2SQL: jieba 提取关键词
        NL2SQL->>DB: Milvus 向量检索 字段匹配
        NL2SQL->>DB: ES 全文检索 维度值匹配
        DB-->>NL2SQL: 候选字段 + 候选维度值
        NL2SQL->>NL2SQL: LLM 筛选相关表和字段

        Note over NL2SQL: 阶段2 SQL生成 + 安全校验
        NL2SQL->>NL2SQL: LLM 生成 SQL
        NL2SQL->>NL2SQL: 正则 + SQLGlot AST 校验
        NL2SQL->>DB: EXPLAIN 验证
        DB-->>NL2SQL: EXPLAIN 通过/失败自动修正
        NL2SQL->>DB: 执行 SELECT(只读账号)
        DB-->>NL2SQL: 查询结果

        NL2SQL-->>Agent: 结构化数据
        Agent->>Card: 渲染 Interactive Card
        Card-->>FS: 流式推送 逐步填充
        FS-->>User: 结果逐步展现
    end

    Note over Agent: 全程 MonitoringStats LLM调用+Skill耗时+错误数
```

## 二、六大业务场景路由流程

```mermaid
graph TD
    START("用户在飞书群 @机器人<br/>自然语言提问")
    GUARD{"Guardrails 安检<br/>敏感词或非电商话题？"}
    REJECT("拦截<br/>返回友好提示")
    ROUTER{"意图识别<br/>LangGraph Router"}
    
    GOODS["商品分析<br/>SKU 销量/趋势/排行"]
    AD_SKILL["广告分析<br/>ROI/花费/转化"]
    INVENTORY["库存预警<br/>水位/安全线/滞销"]
    NL2SQL_SKILL["NL2SQL 即席查询<br/>任意 ad-hoc 问题"]
    MARKETING["营销文案<br/>AI 生成推广文案"]
    FILE_SKILL["文件分析<br/>上传 Excel/PDF 问答"]

    CARD("飞书 Interactive Card<br/>流式渲染返回")

    START --> GUARD
    GUARD -->|"敏感/非电商"| REJECT
    GUARD -->|"通过"| ROUTER
    ROUTER -->|"商品相关"| GOODS
    ROUTER -->|"广告相关"| AD_SKILL
    ROUTER -->|"库存相关"| INVENTORY
    ROUTER -->|"复杂即席查询"| NL2SQL_SKILL
    ROUTER -->|"营销文案"| MARKETING
    ROUTER -->|"文件上传"| FILE_SKILL
    
    GOODS --> CARD
    AD_SKILL --> CARD
    INVENTORY --> CARD
    NL2SQL_SKILL --> CARD
    MARKETING --> CARD
    FILE_SKILL --> CARD
```

## 三、NL2SQL 管线（核心亮点）

> 拆为两张图：管线概览走通全流程，安全防线放大看细节。

### 3a. 核心管线概览（4 阶段）

```mermaid
graph LR
    Q("用户问题<br/>毛利率超40%且库存<br/>低于安全线的SKU?")

    Q --> A["1. 关键词提取<br/>jieba 分词"]

    A --> B["2a. Milvus 向量检索<br/>字段名/指标匹配<br/>毛利率->profit_margin"]
    A --> C["2b. ES 全文检索<br/>维度取值匹配<br/>华东区->region_name"]

    B --> D["3. LLM 筛选<br/>确定表与字段"]
    C --> D

    D --> E["4. LLM 生成 SQL"]

    E --> F{"5. 安全校验<br/>五道防线"}

    F -->|"通过"| G["6. 只读执行"]
    G --> H("飞书 Card<br/>返回结果")

    F -.->|"拦截"| X("拒绝执行")

    F -.->|"修正"| R["回注错误<br/>LLM 重生成"]
    R -.-> E
```

### 3b. 安全五道防线（放大详图）

```mermaid
graph TD
    SQL_IN("LLM 生成的 SQL 进入")

    SQL_IN --> L1{"防线1<br/>Prompt 约束<br/>限定 SELECT 语句?"}
    L1 -->|"否"| REJ1("拦截")
    L1 -->|"是"| L2{"防线2<br/>正则扫描<br/>含 DROP/DELETE?"}
    L2 -->|"命中"| REJ2("拦截")
    L2 -->|"安全"| L3{"防线3<br/>SQLGlot AST<br/>根节点=SELECT?"}
    L3 -->|"否"| REJ3("拦截")
    L3 -->|"是"| L4{"防线4<br/>EXPLAIN 验证<br/>数据库执行通过?"}
    L4 -->|"失败"| FIX["自动修正<br/>错误回注 Prompt<br/>LLM 重新生成<br/>修正率约 85%"]
    FIX -.->|"重试"| SQL_IN
    L4 -->|"通过"| L5["防线5<br/>只读数据库账号<br/>执行 SELECT"]
    L5 --> DONE("返回查询结果")

    style REJ1 fill:#ffcdd2,stroke:#d81b60,stroke-width:2px
    style REJ2 fill:#ffcdd2,stroke:#d81b60,stroke-width:2px
    style REJ3 fill:#ffcdd2,stroke:#d81b60,stroke-width:2px
    style FIX fill:#fff9c4,stroke:#f9a825,stroke-width:2px
    style DONE fill:#c8e6c9,stroke:#388e3c,stroke-width:2px
```

## 四、MCP 工具调用流程（适配器模式）

```mermaid
sequenceDiagram
    participant Skill as Agent Skill
    participant MCP as MCP 标准接口
    participant Router as 适配器路由器
    participant ERP as ERP 适配器

    Skill->>MCP: get_inventory(sku_id, platform)
    Note over MCP: 工具签名固定不变<br/>底层实现可替换
    MCP->>Router: 根据 platform 参数路由

    alt platform = mock
        Router->>ERP: Mock 适配器
        ERP-->>Router: 模拟数据
    end

    alt platform = dxmi
        Router->>ERP: 店小秘 API
        ERP-->>Router: 实时库存数据
    end

    alt platform = lx
        Router->>ERP: 领星 API
        ERP-->>Router: 实时库存数据
    end

    alt platform = amazon
        Router->>ERP: Amazon SP-API
        ERP-->>Router: 实时库存数据
    end

    Router-->>MCP: 标准化 InventoryResult
    MCP-->>Skill: 库存数据
    Note over ERP: Agent 图代码零改动<br/>换 ERP 只需加新适配器
```

## 五、结果呈现流程（飞书 Interactive Card 流式渲染）

```mermaid
graph LR
    A["Agent 开始执行"]
    B["① 先推空卡片<br/>显示 正在分析..."]
    C["② 填充关键词<br/>识别结果"]
    D["③ 填充 SQL 生成<br/>完成提示"]
    E["④ 填充查询结果<br/>数据表格"]
    F["⑤ 卡片完成<br/>图表呈现"]
    G["运营看到结果<br/>逐步展现<br/>体验优于干等"]

    A --> B --> C --> D --> E --> F --> G
```

## 业务流程速查

| 阶段 | 关键步骤 | 技术实现 | 时间 |
|------|----------|----------|------|
| 接收 | 飞书群 @机器人 | WebSocket 长连接 | 实时 |
| 安检 | 敏感词 + 话题过滤 | Guardrails | <100ms |
| 路由 | 意图识别 → 6 大场景 | LangGraph Router | <500ms |
| 检索 | jieba → Milvus + ES 双路 | 向量 + 全文混合检索 | ~1s |
| 生成 | LLM 选表 → 生成 SQL | Prompt Engineering | ~2s |
| 安全 | 五道防线逐一校验 | 正则 + AST + EXPLAIN | ~500ms |
| 执行 | 只读账号 SELECT | MySQL 数仓 | <1s |
| 返回 | Interactive Card 流式 | 飞书卡片 API | 流式，边算边出 |
| 总计 | 一次查询平均 | 端到端 | **~5s** |
