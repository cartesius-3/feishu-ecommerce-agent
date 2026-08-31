"""文件解析工具（Excel/CSV/PDF/Word → 结构化文本）。

FileParserTool：
  parse_local_file()    — 解析为列统计 + 样本数据
  format_file_summary() — 格式化为给 LLM 的摘要
load_file               — LangGraph 节点封装（workflow 引用）
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from app.agent.state import AgentState


class FileParserTool:
    SUPPORTED = {".xlsx", ".xls", ".csv", ".pdf", ".docx"}

    def parse_local_file(self, path: str) -> Dict[str, Any]:
        """解析文件 → {filename, columns, stats, samples}。"""
        p = Path(path)
        if p.suffix.lower() not in self.SUPPORTED:
            raise ValueError(f"不支持的文件类型：{p.suffix}（支持 {'/'.join(self.SUPPORTED)}）")

        if p.suffix.lower() in (".xlsx", ".xls", ".csv"):
            return self._parse_table(p)
        if p.suffix.lower() == ".docx":
            return self._parse_docx(p)
        return self._parse_pdf(p)

    # ----- 表格类 -----
    def _parse_table(self, p: Path) -> Dict[str, Any]:
        try:
            import pandas as pd
        except ImportError:
            raise RuntimeError("解析 Excel/CSV 需要安装 pandas")
        df = pd.read_excel(p) if p.suffix.lower() != ".csv" else pd.read_csv(p)
        # 采样 1000 行（诚实划偏：非全表统计）
        sample_df = df.head(1000)
        stats = {}
        for col in df.columns:
            s = sample_df[col]
            if s.dtype.kind in "if":  # 数值列
                stats[str(col)] = {
                    "type": "numeric", "mean": round(s.mean(), 2),
                    "min": round(s.min(), 2), "max": round(s.max(), 2),
                    "std": round(s.std(), 2), "nulls": int(s.isna().sum()),
                }
            else:  # 文本列：算唯一值 + 去重样本
                uniq = s.dropna().unique()[:10]
                stats[str(col)] = {
                    "type": "text", "unique_values": int(s.nunique()),
                    "samples": [str(u) for u in uniq],
                }
        return {"filename": p.name, "rows": len(df), "columns": list(df.columns),
                "stats": stats, "sample": df.head(5).to_dict(orient="records")}

    # ----- Word / PDF（纯文本抽取）-----
    def _parse_docx(self, p: Path) -> Dict[str, Any]:
        try:
            from docx import Document
        except ImportError:
            raise RuntimeError("解析 Word 需要安装 python-docx")
        doc = Document(str(p))
        text = "\n".join(par.text for par in doc.paragraphs if par.text.strip())
        return {"filename": p.name, "type": "docx", "chars": len(text),
                "preview": text[:2000]}

    def _parse_pdf(self, p: Path) -> Dict[str, Any]:
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            raise RuntimeError("解析 PDF 需要安装 PyPDF2")
        reader = PdfReader(str(p))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return {"filename": p.name, "type": "pdf", "pages": len(reader.pages),
                "chars": len(text), "preview": text[:2000]}

    def format_file_summary(self, parsed: Dict[str, Any]) -> str:
        """格式化摘要，喂给 LLM（数字来自解析器，LLM 只配词）。"""
        lines = [f"文件名：{parsed.get('filename')}"]
        if parsed.get("rows") is not None:
            lines.append(f"行数：{parsed['rows']}，列：{', '.join(map(str, parsed['columns']))}")
        if parsed.get("stats"):
            for col, info in list(parsed["stats"].items())[:10]:
                lines.append(f"列[{col}] {info}")
        if parsed.get("preview"):
            lines.append(f"内容预览：{parsed['preview'][:500]}")
        return "\n".join(lines)


_file_parser = FileParserTool()


def load_file(state: AgentState) -> Dict[str, Any]:
    """LangGraph 节点：若有上传文件则解析并格式化摘要。"""
    path = state.get("file_path")
    if not path:
        return {}
    parsed = _file_parser.parse_local_file(path)
    return {"file_content": _file_parser.format_file_summary(parsed)}
