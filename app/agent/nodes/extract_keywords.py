"""NL2SQL 节点：关键词提取。

jieba TF-IDF + 词性过滤，保留原始 query。未装 jieba 时退化为简单分词。
"""

from typing import Any, Dict, List

from app.agent.state import AgentState


def extract_keywords(state: AgentState) -> Dict[str, Any]:
    query = state.get("user_input", "")
    try:
        import jieba.analyse

        keywords: List[str] = jieba.analyse.extract_tags(
            query, topK=10,
            allowPOS=("n", "nr", "ns", "nt", "nz", "v", "vn", "a", "an", "eng"),
        )
    except ImportError:
        # 未安装 jieba：简单分词兜底（中文按常见分隔符切分）
        import re

        keywords = [w for w in re.split(r"[\s,，。；;、]", query) if len(w) > 1]

    keywords = list(dict.fromkeys([*keywords, query]))  # 保留原始 query + 去重
    return {"keywords": keywords}
