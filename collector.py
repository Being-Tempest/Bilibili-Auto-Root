"""
目标采集模块（学习版）。

从指定直播间采集有消费记录的用户（公开接口，无需登录）：
  - 高能榜（金瓜子贡献榜）：在线送礼用户
  - 大航海（舰队榜）：开通舰长/提督/总督的用户

输出去重后的 UID 列表，写入 data/targets_pool.json。
"""

import json
import time
import logging
from typing import Optional

from bilibili_api import sync
from bilibili_api.live import LiveRoom

from config import (
    get_credential,
    TARGET_ROOM_IDS,
    MAX_USERS_PER_ROOM,
    DATA_DIR,
    TARGETS_POOL_FILE,
)

logger = logging.getLogger(__name__)


def _get_anchor_uid(room: LiveRoom) -> Optional[int]:
    """从房间播放信息中获取主播 UID（ruid），供排名接口使用。"""
    try:
        play_info = sync(room.get_room_play_info())
        anchor_info = play_info.get("anchor_info", {}) if isinstance(play_info, dict) else {}
        uid = anchor_info.get("uid")
        if uid:
            return int(uid)
    except Exception as e:
        logger.warning("获取房间 %s 主播 uid 失败: %s", room.room_display_id, e)

    # 回退：尝试从 room_info 取
    try:
        info = sync(room.get_room_info())
        room_info = info.get("room_info", {}) if isinstance(info, dict) else {}
        uid = room_info.get("uid")
        if uid:
            return int(uid)
    except Exception as e:
        logger.warning("回退获取 uid 也失败: %s", e)

    return None


def collect_gaonengbang(room: LiveRoom, ruid: int, max_users: int = MAX_USERS_PER_ROOM) -> list[dict]:
    """
    采集高能榜（在线金瓜子贡献榜）用户。

    Returns:
        list[dict]: [{"uid": int, "uname": str, "score": int, "source": "gaonengbang"}, ...]
    """
    users: list[dict] = []
    page = 1

    while len(users) < max_users:
        try:
            result = sync(room.get_gaonengbang(page=page))
        except Exception as e:
            logger.error("高能榜 page=%d 失败: %s", page, e)
            break

        items = result.get("OnlineRankItem", []) if isinstance(result, dict) else []
        if not items:
            break

        for item in items:
            if len(users) >= max_users:
                break
            uid = item.get("uid")
            uname = item.get("name", "")
            score = item.get("score", 0)
            if uid:
                users.append({
                    "uid": int(uid),
                    "uname": str(uname),
                    "score": int(score),
                    "source": "gaonengbang",
                })

        page += 1
        if page > 10:  # 安全上限
            break
        time.sleep(0.5)  # 请求间隔，礼貌请求

    logger.info("高能榜采集: room=%s, users=%d", room.room_display_id, len(users))
    return users


def collect_dahanghai(room: LiveRoom, max_users: int = MAX_USERS_PER_ROOM) -> list[dict]:
    """
    采集大航海（舰队）用户。

    Returns:
        list[dict]: [{"uid": int, "uname": str, "guard_level": int, "source": "dahanghai"}, ...]
    """
    users: list[dict] = []
    page = 1

    while len(users) < max_users:
        try:
            result = sync(room.get_dahanghai(page=page))
        except Exception as e:
            logger.error("大航海 page=%d 失败: %s", page, e)
            break

        # api 返回结构: {"list": [...], "top3": [...]}
        items = result.get("list", []) if isinstance(result, dict) else []
        if not items:
            break

        for item in items:
            if len(users) >= max_users:
                break
            uid = item.get("uid")
            uname = item.get("username", "")
            guard_level = item.get("guard_level", 0)
            if uid:
                users.append({
                    "uid": int(uid),
                    "uname": str(uname),
                    "guard_level": int(guard_level),
                    "source": "dahanghai",
                })

        page += 1
        if page > 10:
            break
        time.sleep(0.5)

    logger.info("大航海采集: room=%s, users=%d", room.room_display_id, len(users))
    return users


def collect_from_room(room_id: int, credential=None) -> list[dict]:
    """
    从单个直播间采集所有目标用户。
    """
    room = LiveRoom(room_id, credential=credential)
    all_users: list[dict] = []

    ruid = _get_anchor_uid(room)
    if ruid:
        gaoneng_users = collect_gaonengbang(room, ruid=ruid)
        all_users.extend(gaoneng_users)
    else:
        logger.warning("房间 %s 无法获取主播 uid，跳过高能榜", room_id)

    dahanghai_users = collect_dahanghai(room)
    all_users.extend(dahanghai_users)

    return all_users


def deduplicate_users(users: list[dict]) -> list[dict]:
    """按 UID 去重，保留消费信号更强的记录。"""
    seen: dict[int, dict] = {}
    # 数据源优先级：dahanghai > gaonengbang（舰队消费更高）
    priority = {"dahanghai": 2, "gaonengbang": 1}

    for user in users:
        uid = user["uid"]
        if uid not in seen:
            seen[uid] = user
        else:
            # 保留优先级更高的来源
            existing_pri = priority.get(seen[uid]["source"], 0)
            new_pri = priority.get(user["source"], 0)
            if new_pri > existing_pri:
                seen[uid] = user

    return list(seen.values())


def save_targets(users: list[dict]) -> int:
    """保存到 targets_pool.json，返回写入条数。"""
    TARGETS_POOL_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TARGETS_POOL_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    return len(users)


def run_collect(room_ids: Optional[list[int]] = None) -> list[dict]:
    """
    执行全量采集流程。

    Args:
        room_ids: 要扫描的直播间 ID 列表，不传则使用 config 中的 TARGET_ROOM_IDS。

    Returns:
        去重后的用户列表。
    """
    if room_ids is None:
        room_ids = TARGET_ROOM_IDS

    if not room_ids:
        logger.warning("TARGET_ROOM_IDS 为空，请先在 config.py 中配置目标直播间")
        return []

    credential = get_credential()
    all_users: list[dict] = []

    for room_id in room_ids:
        logger.info("开始采集房间: %s", room_id)
        try:
            users = collect_from_room(room_id, credential)
            all_users.extend(users)
        except Exception as e:
            logger.exception("房间 %s 采集异常: %s", room_id, e)
        time.sleep(1.0)  # 房间间休息

    unique_users = deduplicate_users(all_users)
    count = save_targets(unique_users)
    logger.info("采集完成: 总计 %d 个直播间, %d 个不重复用户", len(room_ids), count)
    return unique_users


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_collect()
