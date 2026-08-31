"""飞书 WebSocket 接入（独立子进程）。

设计要点：
- lark_oapi WSClient 长连接（无需公网 IP/域名/SSL——相比 Webhook 的核心优势）
- 独立子进程运行（subprocess.Popen 启动），主进程挂掉不影响消息接收
- 消息队列 + 守护线程消费：@提及检测 → 文件下载解析 → Guardrails → agent.invoke → 回复

运行：python -m app.tools.feishu_ws
"""

import queue
import threading

from app.config import settings

_message_queue: "queue.Queue[dict]" = queue.Queue()


def _on_message(event) -> None:
    """飞书消息事件回调：入队，交给消费线程处理。"""
    _message_queue.put(event)


def _process_messages() -> None:
    """守护线程：从队列取消息并处理。"""
    from app.agent.workflow import build_graph
    from app.tools.feishu_tool import feishu_tool
    from app.tools.guardrails import check_input

    graph = build_graph()

    while True:
        event = _message_queue.get()
        try:
            message = event.event.message
            chat_type = event.event.message.chat_type
            text = message.content  # 简化：真实为 JSON 解析 text
            message_id = message.message_id
            chat_id = message.chat_id

            # 群聊必须 @ 才响应
            if chat_type == "group" and "@_user_" not in text:
                continue

            # 输入安全
            if reason := check_input(text):
                feishu_tool.reply_message(message_id, f"⚠️ {reason}")
                continue

            # Agent 执行
            state = graph.invoke({
                "user_input": text,
                "conversation_id": chat_id,
                "file_path": _download_attachment(event, message_id),
            })
            feishu_tool.reply_message(message_id, state.get("answer", ""))
        except Exception as e:  # noqa: BLE001 —— 单条消息失败不拖垮线程
            print(f"[feishu_ws] process error: {e}")


def _download_attachment(event, message_id: str) -> str:
    """消息含文件时下载到本地，返回路径（无文件返回空串）。"""
    # 真实实现：遍历 message.mentions / attachments，调
    # feishu_tool.download_file() 落盘到 data/inbox/
    return ""


def start() -> None:
    """启动 WS 长连接 + 消费线程（独立子进程入口）。"""
    if not settings.feishu_app_id or not settings.feishu_app_secret:
        print("[feishu_ws] 未配置 FEISHU_APP_ID/SECRET，mock 模式：不建立真实连接")
        return

    import lark_oapi as lark

    client = lark.Client.builder() \
        .app_id(settings.feishu_app_id) \
        .app_secret(settings.feishu_app_secret) \
        .log_level(lark.LogLevel.INFO) \
        .build()

    handler = lark.EventDispatcherHandler.builder("", "") \
        .register_p2_im_message_receive_v1(_on_message) \
        .build()

    # 消费线程
    threading.Thread(target=_process_messages, daemon=True).start()

    # 长连接（阻塞）
    conn = lark.ws.Client(settings.feishu_app_id, settings.feishu_app_secret,
                          event_handler=handler)
    conn.start()


if __name__ == "__main__":
    start()
