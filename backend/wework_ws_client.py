# -*- coding: utf-8 -*-
"""
企业微信智能机器人 WebSocket 长连接客户端

协议：developer.work.weixin.qq.com/document/60904
连接：wss://openws.work.weixin.qq.com
认证：aibot_subscribe(bot_id + secret)
接收：aibot_msg_callback
回复：aibot_respond_msg
心跳：每30秒 ping

依赖：pip install websockets
"""

import os
import sys
import json
import uuid
import asyncio
import logging
import re
from typing import Optional

try:
    import websockets
    from websockets.asyncio.client import connect as ws_connect
    from websockets.exceptions import ConnectionClosed, WebSocketException
except ImportError:
    print("请先安装 websockets: pip install websockets")
    sys.exit(1)

# ── 日志 ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("wework_ws")

# ── 配置 ──────────────────────────────────────────────────
WS_URL = "wss://openws.work.weixin.qq.com"
BOT_ID = "aibah14B_kW8rZto85NBfWcn7b1FvkWdGHi"
SECRET = "CFPPOmrU4vVEnLK5TPGOJuYsNjRoQNXmyOKeqDMtFo4"

HEARTBEAT_INTERVAL = 30          # 心跳间隔（秒）
RECONNECT_BASE_DELAY = 1         # 重连基础延迟（秒）
RECONNECT_MAX_DELAY = 60         # 重连最大延迟（秒）
RECONNECT_BACKOFF_FACTOR = 2     # 指数退避因子

TOP_K = 5                        # 搜索结果返回条数
MAX_REPLY_LENGTH = 2048          # 回复内容最大长度（企微限制约 2048）

# ── 导入 app 模块 ─────────────────────────────────────────
# 确保 backend 目录在 sys.path 中，以便 import app
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

try:
    from app import match_score, load_resources
    logger.info("已从 app.py 导入 match_score 和 load_resources")
except ImportError as e:
    logger.error(f"无法导入 app 模块: {e}")
    sys.exit(1)


# ── 工具函数 ──────────────────────────────────────────────

def strip_at_prefix(text: str) -> str:
    """去掉 @机器人 前缀（形如 @xxx 或 @xxx  等）"""
    # 匹配 @ 开头后跟非空白字符（含全角空格 U+2005 等）
    cleaned = re.sub(r'^@\S+\s*', '', text).strip()
    return cleaned


def format_results(scored_results: list) -> str:
    """
    将 match_score 排序后的 [(score, resource), ...] 格式化为回复文本。
    只取 Top-K，每行格式：[标题] - [类型]
    """
    if not scored_results:
        return "未找到匹配的资源，请尝试换个方式提问。"

    # 取 TOP_K 条（只保留 score > 0 的）
    top = [(s, r) for s, r in scored_results[:TOP_K] if s > 0]

    if not top:
        return "未找到匹配的资源，请尝试换个方式提问。"

    lines = ["为您找到以下相关资源："]
    for i, (score, r) in enumerate(top, 1):
        title = r.get("title", "无标题")
        file_type = r.get("file_type", "other")
        resource_type = r.get("resource_type", "")
        type_label = file_type if resource_type != "link" else "链接"
        lines.append(f"{i}. [{title}] - {type_label}")

    reply = "\n".join(lines)
    if len(reply) > MAX_REPLY_LENGTH:
        reply = reply[:MAX_REPLY_LENGTH - 3] + "..."

    return reply


def do_search(query: str) -> tuple:
    """
    执行资源搜索。返回 (scored_list, scored_sorted_list)
    scored_list 是 [(score, resource), ...] 并按分数降序排列
    """
    resources = load_resources()
    if not resources:
        return [], []

    scored = []
    for r in resources:
        s = match_score(query, r)
        scored.append((s, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


# ── 消息处理器 ────────────────────────────────────────────

class MessageHandler:
    """企业微信 WebSocket 消息处理"""

    def __init__(self):
        self.ping_task: Optional[asyncio.Task] = None

    def build_subscribe_frame(self) -> str:
        """构建订阅帧"""
        frame = {
            "cmd": "aibot_subscribe",
            "headers": {"req_id": str(uuid.uuid4())},
            "body": {
                "bot_id": BOT_ID,
                "secret": SECRET,
            },
        }
        return json.dumps(frame, ensure_ascii=False)

    def build_respond_frame(
        self, req_id: str, msgid: str, content: str, msgtype: str = "text"
    ) -> str:
        """构建回复帧"""
        frame = {
            "cmd": "aibot_respond_msg",
            "headers": {"req_id": req_id},
            "body": {
                "msgid": msgid,
                "msgtype": msgtype,
                "text": {"content": content},
            },
        }
        return json.dumps(frame, ensure_ascii=False)

    def build_stream_frame(self, req_id: str, msgid: str, content: str) -> str:
        """构建流式回复帧"""
        frame = {
            "cmd": "aibot_respond_msg",
            "headers": {"req_id": req_id},
            "body": {
                "msgid": msgid,
                "msgtype": "stream",
                "stream": {"id": str(uuid.uuid4()), "finish": False, "content": content},
            },
        }
        return json.dumps(frame, ensure_ascii=False)

    def build_stream_finish_frame(self, req_id: str, msgid: str, content: str, stream_id: str) -> str:
        """构建流式结束帧"""
        frame = {
            "cmd": "aibot_respond_msg",
            "headers": {"req_id": req_id},
            "body": {
                "msgid": msgid,
                "msgtype": "stream",
                "stream": {"id": stream_id, "finish": True, "content": content},
            },
        }
        return json.dumps(frame, ensure_ascii=False)

    async def handle_message(self, ws, raw: str):
        """处理收到的消息帧"""
        try:
            frame = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"收到非 JSON 消息: {raw[:200]}")
            return

        cmd = frame.get("cmd", "")
        headers = frame.get("headers", {})
        body = frame.get("body", {})
        req_id = headers.get("req_id", "")

        if cmd == "aibot_subscribe_resp":
            # 订阅响应
            self._handle_subscribe_resp(body)

        elif cmd == "aibot_msg_callback":
            # 用户消息回调
            await self._handle_msg_callback(ws, body, req_id)

        elif cmd == "aibot_event_callback":
            # 事件回调（enter_chat 等）
            await self._handle_event_callback(ws, body, req_id)

        elif cmd == "pong":
            logger.debug("收到 pong")

        else:
            logger.debug(f"收到未处理的消息类型: {cmd}")

    def _handle_subscribe_resp(self, body: dict):
        """处理订阅响应"""
        errcode = body.get("errcode", -1)
        errmsg = body.get("errmsg", "")
        if errcode == 0:
            logger.info(f"订阅成功！BotID: {BOT_ID}")
        else:
            logger.error(f"订阅失败: errcode={errcode}, errmsg={errmsg}")

    async def _handle_msg_callback(self, ws, body: dict, req_id: str):
        """处理用户消息回调"""
        msgid = body.get("msgid", "")
        msgtype = body.get("msgtype", "")

        logger.info(f"收到消息: msgid={msgid}, msgtype={msgtype}")

        if msgtype == "text":
            text_body = body.get("text", {})
            content = text_body.get("content", "")
            # 去掉 @机器人 前缀
            query = strip_at_prefix(content)
            logger.info(f"用户查询: {query}")

            if not query:
                reply = "请输入您想查询的问题。"
            else:
                scored = do_search(query)
                reply = format_results(scored)

            frame = self.build_respond_frame(req_id, msgid, reply)
            await ws.send(frame)
            logger.info(f"已回复: msgid={msgid}")

        elif msgtype == "stream":
            # stream 类型：用户可能发了流式消息，暂不支持
            frame = self.build_respond_frame(
                req_id, msgid, "暂不支持此消息类型，请发送文字。"
            )
            await ws.send(frame)

        else:
            frame = self.build_respond_frame(
                req_id, msgid, "暂不支持此消息类型，请发送文字。"
            )
            await ws.send(frame)

    async def _handle_event_callback(self, ws, body: dict, req_id: str):
        """处理事件回调"""
        event_type = body.get("event_type", "")
        logger.info(f"收到事件: event_type={event_type}")

        if event_type == "enter_chat":
            msgid = body.get("msgid", "")
            welcome = (
                "你好！我是小雷没摸鱼资源库助手。\n"
                "直接发送关键词即可搜索资源库，如「产品设计素材」「Python 教程」等。"
            )
            frame = self.build_respond_frame(req_id, msgid, welcome)
            await ws.send(frame)
            logger.info("已发送欢迎语")


# ── WebSocket 连接管理 ────────────────────────────────────

class WeworkWSClient:
    """企业微信 WebSocket 客户端"""

    def __init__(self):
        self.handler = MessageHandler()
        self.ws = None
        self.ping_task: Optional[asyncio.Task] = None
        self._running = False

    async def ping_loop(self, ws):
        """心跳循环：每 HEARTBEAT_INTERVAL 秒发送 ping"""
        try:
            while self._running:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                if ws and not ws.close_code:
                    try:
                        await ws.send(json.dumps({"cmd": "ping"}))
                        logger.debug("发送 ping")
                    except (ConnectionClosed, WebSocketException):
                        logger.warning("心跳发送失败，连接可能已断开")
                        break
        except asyncio.CancelledError:
            pass

    async def message_loop(self, ws):
        """消息接收循环"""
        try:
            async for raw in ws:
                if isinstance(raw, str):
                    await self.handler.handle_message(ws, raw)
                elif isinstance(raw, bytes):
                    # 官方协议为 JSON 文本，bytes 也尝试解码
                    try:
                        text = raw.decode("utf-8")
                        await self.handler.handle_message(ws, text)
                    except UnicodeDecodeError:
                        logger.warning(f"收到无法解码的二进制数据，长度: {len(raw)}")
        except ConnectionClosed as e:
            logger.info(f"连接关闭: code={e.code}, reason={e.reason}")
        except WebSocketException as e:
            logger.error(f"WebSocket 异常: {e}")

    async def connect(self):
        """建立 WebSocket 连接并进入主循环"""
        async with ws_connect(WS_URL, ping_interval=None) as ws:
            self.ws = ws
            logger.info(f"已连接到 {WS_URL}")

            # 发送订阅帧
            sub_frame = self.handler.build_subscribe_frame()
            logger.info(f"发送订阅帧...")
            await ws.send(sub_frame)

            # 启动心跳
            self._running = True
            self.ping_task = asyncio.create_task(self.ping_loop(ws))

            try:
                await self.message_loop(ws)
            finally:
                self._running = False
                if self.ping_task:
                    self.ping_task.cancel()
                    try:
                        await self.ping_task
                    except asyncio.CancelledError:
                        pass
                self.ping_task = None

    async def run_forever(self):
        """持续运行，自动重连（指数退避）"""
        attempt = 0
        while True:
            try:
                await self.connect()
                # 正常关闭，重置重连计数
                attempt = 0
                delay = RECONNECT_BASE_DELAY
            except (OSError, WebSocketException, asyncio.TimeoutError) as e:
                attempt += 1
                delay = min(
                    RECONNECT_BASE_DELAY * (RECONNECT_BACKOFF_FACTOR ** (attempt - 1)),
                    RECONNECT_MAX_DELAY,
                )
                logger.error(f"连接失败（第 {attempt} 次）: {e}")
                logger.info(f"将在 {delay} 秒后重连...")
                await asyncio.sleep(delay)
            except KeyboardInterrupt:
                logger.info("收到中断信号，退出")
                break


# ── 入口 ──────────────────────────────────────────────────

async def main():
    client = WeworkWSClient()
    await client.run_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("客户端已停止")
