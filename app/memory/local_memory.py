"""对话历史（LocalMemory）：SQLite 持久化 + LangGraph 节点封装。

load_history / save_history 作为图节点函数，由 workflow 引用。
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from app.agent.state import AgentState
from app.config import settings


class LocalMemory:
    """SQLite 会话存储。表：conversations(conversation_id, role, content, ts)。"""

    def __init__(self, db_path: str = "") -> None:
        path = Path(db_path or settings.sqlite_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                ts TEXT NOT NULL
            )"""
        )
        self._conn.commit()

    def get_history(self, conversation_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT role, content FROM conversations "
            "WHERE conversation_id=? ORDER BY rowid DESC LIMIT ?",
            (conversation_id, limit),
        ).fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def append(self, conversation_id: str, role: str, content: str) -> None:
        self._conn.execute(
            "INSERT INTO conversations (conversation_id, role, content, ts) VALUES (?,?,?,?)",
            (conversation_id, role, content, datetime.now().isoformat()),
        )
        self._conn.commit()


_local_memory = LocalMemory()


def load_history(state: AgentState) -> Dict[str, Any]:
    cid = state.get("conversation_id", "default")
    history = _local_memory.get_history(cid, settings.conversation_history)
    return {"history": history}


def save_history(state: AgentState) -> Dict[str, Any]:
    cid = state.get("conversation_id", "default")
    _local_memory.append(cid, "user", state.get("user_input", ""))
    _local_memory.append(cid, "assistant", state.get("answer", ""))
    return {}
