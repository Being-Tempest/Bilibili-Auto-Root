"""
发送示例（学习版）。

演示用 bilibili-api 向单个用户发送一条私信。
本模块刻意不提供批量循环、速率对抗等"规模化"能力——
工具的作用是帮助你克制的、一次一条地与人建立连接。

用法：
  python sender.py <uid> [消息文本]
  不带消息时，自动从 templates 生成一条打招呼话术。

前置：发送需要你自己的 Cookie，在仓库根目录创建 credentials.json：
  {"sessdata": "...", "bili_jct": "...", "buvid3": "..."}
"""

import json
import sys
import logging
from datetime import datetime
from typing import Optional

from config import get_credential, MAX_MSG_LEN, SENT_LOG_FILE

logger = logging.getLogger(__name__)


def _load_sent_log() -> list:
    """加载发送日志。"""
    if not SENT_LOG_FILE.exists():
        return []
    try:
        with open(SENT_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _append_log(entry: dict) -> None:
    """追加一条发送记录。"""
    log = _load_sent_log()
    log.append(entry)
    SENT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SENT_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def truncate_message(message: str, limit: int = MAX_MSG_LEN) -> str:
    """超长截断，B站私信约 200 字上限。"""
    if len(message) <= limit:
        return message
    logger.warning("消息长度 %d 超过上限 %d，已截断", len(message), limit)
    return message[:limit]


def send_one(uid: int, message: str) -> dict:
    """
    向单个用户发送一条私信。

    Returns:
        {"success": bool, "uid": int, "response": dict|None, "error": str|None}
    """
    from bilibili_api import sync
    from bilibili_api.user import User

    credential = get_credential()
    if credential is None:
        logger.error("未配置凭据：请在仓库根目录创建 credentials.json（见 README）")
        return {"success": False, "uid": uid, "response": None, "error": "credentials.json 未配置"}

    message = truncate_message(message)
    try:
        user = User(uid, credential=credential)
        result = sync(user.send_msg(message))
        return {"success": True, "uid": uid, "response": result, "error": None}
    except Exception as e:
        return {"success": False, "uid": uid, "response": None, "error": str(e)}


def demo_send(uid: int, message: Optional[str] = None) -> dict:
    """生成一条话术并发送（单次），记录到 sent_log.json。"""
    from templates import generate_message

    if message is None:
        message = generate_message(uid=uid)

    result = send_one(uid, message)

    _append_log({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "uid": uid,
        "message": message,
        "success": result["success"],
        "error": result.get("error"),
    })

    if result["success"]:
        logger.info("已发送 → uid=%s: %s", uid, message[:60])
    else:
        logger.error("发送失败 uid=%s: %s", uid, result.get("error"))
    return result


def get_today_stats() -> dict:
    """今日发送统计（供 status 显示）。"""
    today = datetime.now().strftime("%Y-%m-%d")
    log = _load_sent_log()
    today_log = [e for e in log if e.get("date") == today]
    return {
        "date": today,
        "sent": sum(1 for e in today_log if e.get("success")),
        "failed": sum(1 for e in today_log if not e.get("success")),
        "total": len(today_log),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    if len(sys.argv) < 2:
        print(__doc__)
    else:
        uid = int(sys.argv[1])
        msg = sys.argv[2] if len(sys.argv) > 2 else None
        demo_send(uid, msg)
