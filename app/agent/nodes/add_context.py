"""NL2SQL 节点：补齐上下文（日期 + DB 信息）。

"上个月""近7天"这类相对时间必须落到具体日期口径，否则 LLM 只能猜。
"""

from datetime import date, timedelta
from typing import Any, Dict

from app.agent.state import AgentState
from app.config import settings


def add_extra_context(state: AgentState) -> Dict[str, Any]:
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_start = today.replace(day=1)
    quarter = (today.month - 1) // 3 + 1

    date_info = (
        f"today={today.isoformat()} (weekday={today.strftime('%A')}), "
        f"week_ago={week_ago.isoformat()}, month_start={month_start.isoformat()}, "
        f"quarter=Q{quarter}"
    )
    db_info = (
        f"dialect=sqlite (mock) / mysql 8.0 (prod), "
        f"read_only={settings.dw_read_only}"
    )
    return {"tool_result": {"date_info": date_info, "db_info": db_info}}
