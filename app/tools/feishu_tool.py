"""飞书 REST API 工具（FeishuTool）。

- get_tenant_access_token() — 缓存 7000 秒
- reply_message() / send_message()
- download_file() — 优先 IM 资源 API，回退 Drive API
- get_user_info()
- sync_to_bitable() — 同步监控数据到飞书多维表格

未配置 FEISHU_APP_ID/SECRET 时，方法返回"未配置"占位（mock 模式不调真实 API）。
"""

import time
from typing import Any, Dict, Optional

from app.config import settings


class FeishuTool:
    def __init__(self) -> None:
        self._token: Optional[str] = None
        self._token_expire_at: float = 0.0
        self._base = "https://open.feishu.cn/open-apis"

    # ----- 鉴权 -----
    def get_tenant_access_token(self) -> Optional[str]:
        if not settings.feishu_app_id or not settings.feishu_app_secret:
            return None  # 未配置：mock 模式占位
        if self._token and time.time() < self._token_expire_at:
            return self._token
        import requests

        resp = requests.post(
            f"{self._base}/auth/v3/tenant_access_token/internal",
            json={"app_id": settings.feishu_app_id,
                  "app_secret": settings.feishu_app_secret},
            timeout=10,
        )
        data = resp.json()
        self._token = data.get("tenant_access_token")
        self._token_expire_at = time.time() + data.get("expire", 7200) - 200  # 提前 200s 刷新
        return self._token

    # ----- 消息 -----
    def reply_message(self, message_id: str, content: str) -> Dict[str, Any]:
        token = self.get_tenant_access_token()
        if not token:
            print(f"[MOCK-FEISHU] reply to {message_id}: {content[:80]}…")
            return {"mock": True, "message_id": message_id}
        import requests

        resp = requests.post(
            f"{self._base}/im/v1/messages/{message_id}/reply",
            headers={"Authorization": f"Bearer {token}"},
            json={"msg_type": "text", "content": '{"text": "%s"}' % content},
            timeout=10,
        )
        return resp.json()

    def send_message(self, chat_id: str, content: str, msg_type: str = "text") -> Dict[str, Any]:
        token = self.get_tenant_access_token()
        if not token:
            print(f"[MOCK-FEISHU] send to {chat_id}: {content[:80]}…")
            return {"mock": True, "chat_id": chat_id}
        import requests

        payload = {"receive_id": chat_id, "msg_type": msg_type,
                   "content": '{"text": "%s"}' % content}
        resp = requests.post(
            f"{self._base}/im/v1/messages?receive_id_type=chat_id",
            headers={"Authorization": f"Bearer {token}"},
            json=payload, timeout=10,
        )
        return resp.json()

    # ----- 文件 -----
    def download_file(self, message_id: str, file_key: str) -> Optional[bytes]:
        token = self.get_tenant_access_token()
        if not token:
            return None
        import requests

        resp = requests.get(
            f"{self._base}/im/v1/messages/{message_id}/resources/{file_key}?type=file",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.content
        return None  # 失败时可回退 Drive API

    # ----- 用户 -----
    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        token = self.get_tenant_access_token()
        if not token:
            return {"user_id": user_id, "mock": True}
        import requests

        resp = requests.get(
            f"{self._base}/contact/v3/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        return resp.json()

    # ----- 多维表格监控看板 -----
    def sync_to_bitable(self, records: Dict[str, Any]) -> Dict[str, Any]:
        token = self.get_tenant_access_token()
        if not settings.bitable_app_token or not settings.bitable_table_id:
            print(f"[MOCK-BITABLE] sync records: {records}")
            return {"mock": True, "records": records}
        import requests

        url = (f"{self._base}/bitable/v1/apps/{settings.bitable_app_token}/"
               f"tables/{settings.bitable_table_id}/records/batch_create")
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json={"records": [{"fields": records}]},
            timeout=10,
        )
        return resp.json()


feishu_tool = FeishuTool()
