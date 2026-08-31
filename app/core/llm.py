"""LLM 统一调用层。

- llm_mode=mock：规则式 MockLLM（意图识别用关键词表、SQL 生成用模板拼装），
  无需任何 API Key，全链路可离线演示。
- llm_mode=deepseek/openai：LangChain ChatOpenAI 统一接口
  （DeepSeek / DashScope 均走 OpenAI 兼容协议）。
"""

import re
from functools import lru_cache
from typing import Any, Dict, List, Optional

from app.config import settings

# ---------------------------------------------------------------------------
# Mock 实现（默认）
# ---------------------------------------------------------------------------

# 意图关键词表：命中即归类。顺序即优先级。
_INTENT_RULES: List[tuple] = [
    ("data_query", ["毛利", "毛利率", "ROI", "roas", "销量", "销售额", "库存", "利润",
                    "同比", "环比", "趋势", "占比", "排名", "哪些", "最高", "最低",
                    "广告费", "gmv", "退货", "退款"]),
    ("ads", ["广告", "投放", "roi", "roas", "渠道", "acos", "cpc", "点击率"]),
    ("content", ["写", "文案", "标题", "种草", "带货", "话术", "朋友圈", "小红书", "抖音", "美团"]),
    ("product", ["商品", "sku", "在途", "到货", "缺货", "断货", "详情", "规格"]),
    ("file", ["文件", "表格", "excel", "pdf", "word", "csv", "分析一下", "上传"]),
    ("help", ["你能做什么", "帮助", "你好", "hi", "hello", "你是谁", "有哪些功能", "怎么用"]),
]


class MockLLM:
    """离线规则 LLM。返回结构尽量贴近真实 LLM 输出。"""

    name = "mock"

    def __init__(self) -> None:
        self._intent_rules = _INTENT_RULES

    def complete(self, prompt: str, **kwargs: Any) -> str:
        """通用文本补全。按 prompt 里的标记路由到对应 mock 逻辑。"""
        if "只输出一个意图名" in prompt:
            return self._mock_intent(prompt)
        if "只输出修正后的 SELECT" in prompt:
            return self._mock_correct_sql(prompt)
        if "只输出 SQL" in prompt and "SELECT" in prompt:
            return self._mock_generate_sql(prompt)
        return self._mock_analysis(prompt)

    # ----- 意图识别 -----
    def _mock_intent(self, prompt: str) -> str:
        user_input = self._extract_block(prompt, "用户输入：", "\n").strip()
        text = user_input.lower()
        for intent, keywords in self._intent_rules:
            if any(k in text for k in keywords):
                return intent
        return "help"

    # ----- SQL 生成（从提示里抽取表结构拼 SELECT）-----
    def _mock_generate_sql(self, prompt: str) -> str:
        tables_yaml = self._extract_block(prompt, "表结构（YAML）：", "指标定义")
        query = self._extract_block(prompt, "用户查询：", "硬性要求")
        # 解析 "表.列: 注释" 行，聚合成 {表: [列]}
        table_cols: Dict[str, List[str]] = {}
        for line in tables_yaml.splitlines():
            m = re.match(r"^\s*([a-z_]+)\.([a-z_]+)\s*:", line)
            if not m:
                m = re.match(r"^\s*([a-z_]+)\.([a-z_]+)\s*$", line)
            if m:
                table, col = m.group(1), m.group(2)
                table_cols.setdefault(table, []).append(col)
        if not table_cols:
            return "SELECT 1"
        # 简单拼装：SELECT 非时间列 FROM 第一张事实表
        main_table = next((t for t in ("fact_order", "dim_product", "dim_region") if t in table_cols),
                          list(table_cols.keys())[0])
        cols = [c for c in table_cols[main_table] if c not in ("dt", "date", "created_at")]
        select_cols = cols[:4] if cols else ["*"]
        sql = f"SELECT {', '.join(select_cols)} FROM {main_table}"
        if "dt" in table_cols.get(main_table, []):
            sql += " WHERE dt >= date('now', '-7 day')"
        sql += " LIMIT 50"
        return sql

    def _mock_correct_sql(self, prompt: str) -> str:
        # mock 下修正逻辑：返回原始 SQL（真实实现由 LLM 按 error 修正）
        return self._extract_block(prompt, "原始 SQL：", "错误信息").strip()

    # ----- 分析报告 / 文案（模板）-----
    def _mock_analysis(self, prompt: str) -> str:
        if "商品分析报告" in prompt:
            return ("SKU 近 7 天日均销量平稳，处于健康区间；"
                    "建议关注周末转化高峰，配合补货计划。")
        if "广告优化师" in prompt:
            return ("综合 ROI 约 3.2，其中搜索渠道最优（ROAS 5.1），"
                    "信息流渠道偏低（ROAS 1.8），建议把预算向搜索渠道倾斜 20%。")
        if "文案专家" in prompt:
            return ("【好物安利】这款真的香！\n\n"
                    "实测体验：性价比超高，回购率拉满，姐妹们冲！\n\n"
                    "#好物分享 #种草 #回购")
        if "数据分析师。以下是用户上传文件" in prompt or "列统计" in prompt:
            return ("文件整体质量良好，共 3 列 100 行。其中销售额列波动较大，"
                    "存在 5 行异常低值，建议核查数据口径后做进一步分析。")
        if "电商数据分析师" in prompt or "查询结果（JSON）" in prompt:
            return self._mock_data_answer(prompt)
        if "能力清单" in prompt:
            return ("我能做：1) 查数——@我 问销量/毛利/广告 ROI/库存，自动查库出报告；"
                    "2) 商品/广告分析——SKU 和渠道维度深度分析；"
                    "3) 文案生成——小红书/抖音/美团多平台营销文案；"
                    "4) 文件分析——上传 Excel/PDF/Word 自动出报告；"
                    "5) 库存预警——低库存自动飞书群告警。试试问：'华东区毛利率超过40%的SKU有哪些？'")
        return "收到，已为你处理完成。"

    def _mock_data_answer(self, prompt: str) -> str:
        """基于 query_result 生成带数字的回答（演示用）。"""
        import json as _json

        m = re.search(r"查询结果（JSON）：(\[.*?\])\n", prompt, re.S)
        if not m:
            return "已查询完成，结果为空或无需展示明细。"
        try:
            rows = _json.loads(m.group(1))
        except _json.JSONDecodeError:
            return "已查询完成，结果为空或无需展示明细。"
        if not rows:
            return "查询完成：没有匹配的数据。"
        first = rows[0]
        # 挑数值字段做展示（跳过时间/ID）
        nums = {k: v for k, v in first.items()
                if isinstance(v, (int, float)) and k not in ("order_id", "region_id")}
        if nums:
            top = sorted(nums.items(), key=lambda kv: -abs(kv[1]))[0]
            return (f"查询完成：共 {len(rows)} 行结果。"
                    f"其中 {top[0]} 最高为 {top[1]}，"
                    f"整体分布可查看明细（已附数据）。")
        return f"查询完成：共 {len(rows)} 行结果，详见明细。"

    @staticmethod
    def _extract_block(text: str, start: str, end: str) -> str:
        """截取 start 与 end 之间的文本（end 不存在则取到尾部）。"""
        idx = text.find(start)
        if idx == -1:
            return ""
        idx += len(start)
        jdx = text.find(end, idx)
        return text[idx: jdx if jdx != -1 else len(text)]


# ---------------------------------------------------------------------------
# 真实 LLM（OpenAI 兼容协议）
# ---------------------------------------------------------------------------

def _build_real_llm(base_url: str, api_key: str, model: str, temperature: float = 0.0):
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise RuntimeError("llm_mode != mock 需要安装 langchain-openai")
    return ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=temperature,
    )


class LLMClient:
    """统一 LLM 门面：节点只调 get_llm().complete(prompt)，不关心底层。"""

    def __init__(self) -> None:
        self._mock = MockLLM()
        self._real: Any = None
        self._fallback: Any = None

    def complete(self, prompt: str, *, temperature: Optional[float] = None) -> str:
        if settings.llm_mode == "mock":
            return self._mock.complete(prompt)
        if self._real is None:
            self._real = _build_real_llm(
                settings.llm_base_url, settings.llm_api_key,
                settings.llm_model, temperature if temperature is not None else settings.llm_temperature,
            )
        try:
            resp = self._real.invoke(prompt)
            return resp.content if hasattr(resp, "content") else str(resp)
        except Exception:
            if self._fallback is None and settings.fallback_base_url:
                self._fallback = _build_real_llm(
                    settings.fallback_base_url, settings.fallback_api_key, settings.fallback_model,
                )
            if self._fallback is not None:
                resp = self._fallback.invoke(prompt)
                return resp.content if hasattr(resp, "content") else str(resp)
            raise


@lru_cache
def get_llm() -> LLMClient:
    return LLMClient()
