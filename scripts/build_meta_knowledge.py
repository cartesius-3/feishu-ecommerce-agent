"""构建元数据知识库（半自动四步）。

步骤：
1. 从数仓 information_schema 收集表/列/主外键
2. 叠加业务口径映射（"毛利率"→ gross_profit_rate）
3. 登记示例值与指标公式
4. 落库 meta_knowledge 表

运行：python -m scripts.build_meta_knowledge
"""

from app.models.meta_knowledge import build_meta_knowledge


def main() -> None:
    n = build_meta_knowledge()
    print(f"元数据知识库构建完成：{n} 条记录")


if __name__ == "__main__":
    main()
