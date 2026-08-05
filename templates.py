"""
消息模板（学习版）。

管理打招呼话术模板，支持变量替换与冷却去重。
思路：与其群发，不如对"真正值得认识的人"写一句真诚的话。

变量说明：
  {anchor_name}  — 主播昵称
  {target_nick}  — 目标用户昵称
  {consume_type} — 消费类型描述（"舰长" / "礼物" / "总督" 等）
  {emoji}        — 随机表情
"""

import json
import random
import logging

from config import DATA_DIR

logger = logging.getLogger(__name__)

TEMPLATE_USAGE_FILE = DATA_DIR / "template_usage.json"

TEMPLATES: list[str] = [
    # --- 膜拜/搭讪型 ---
    "大佬好！在{anchor_name}直播间看到你的{consume_type}，太强了，膜拜一下{emoji}",
    "hi～在{anchor_name}那边注意到你了，{consume_type}好耀眼，交个朋友？{emoji}",
    "捕捉一只{anchor_name}的{consume_type}大佬！你好呀{emoji}",
    "哇，在{anchor_name}那边看到你，{consume_type}大佬受我一拜{emoji}",
    "同是{anchor_name}的观众，看到你的{consume_type}忍不住过来打个招呼～",
    "在{anchor_name}那边眼熟你了，{consume_type}选手！认识一下？",
    "抓到你了！{anchor_name}直播间的{consume_type}大佬{emoji}",

    # --- 粉丝共鸣型 ---
    "嗨！我也是{anchor_name}的粉丝，看到你也支持他/她，过来认识一下{emoji}",
    "在{anchor_name}的榜上看到你了！老粉握个手{emoji}",
    "你好呀，我也常看{anchor_name}的直播，发现了同好！",
    "咦，你也是{anchor_name}的观众！缘分啊，认识一下{emoji}",
    "榜上看到你了！{anchor_name}的粉丝都是一家人{emoji}",
    "兄弟你也看{anchor_name}啊！有品位{emoji} 你的{consume_type}太醒目了",

    # --- 礼貌问候型 ---
    "你好！在{anchor_name}直播间注意到你了，打个招呼{emoji}",
    "下午好呀～{anchor_name}那边过来的，看到你了{emoji}",
    "晚上好！{anchor_name}直播间的榜上大佬，来问个好{emoji}",
    "哈喽{target_nick}！在{anchor_name}那边看到你，来打个招呼～",
    "你好你好，{anchor_name}直播间的同好！{emoji}",

    # --- 好奇/互动型 ---
    "嗨，我也看{anchor_name}！你一般什么时间段蹲直播呀{emoji}",
    "在{anchor_name}那边看到你了，你粉他/她多久了呀{emoji}",
    "好奇问下，{anchor_name}直播间你最喜欢哪个环节{emoji}",
    "同看{anchor_name}，你觉得最近直播质量怎么样{emoji}",
    "在榜单上看到你了！你给{anchor_name}送了这么多{consume_type}，真爱粉无疑{emoji}",

    # --- 轻松活泼型 ---
    "滴滴！{anchor_name}粉丝打卡{emoji} 看到你了来蹭个眼熟",
    "嘿！{anchor_name}直播间的{consume_type}大佬突然出现！",
    "在{anchor_name}的榜单上发现了你！就这样水灵灵地来打招呼了{emoji}",
    "滴滴滴——{anchor_name}同好探测雷达响了！你好呀{emoji}",
    "哈！在{anchor_name}那看到你的{consume_type}，火速过来交朋友{emoji}",

    # --- 简短/低调型 ---
    "同看{anchor_name}，有缘认识下{emoji}",
    "{anchor_name}粉丝+1，看到你了",
    "也在看{anchor_name}呀，握爪{emoji}",
    "路过打个招呼，{anchor_name}的同好你好{emoji}",
    "榜单上看到你，过来冒个泡{emoji}",
]

# 随机表情池
EMOJIS: list[str] = [
    "😄", "✋", "👋", "😊", "😂", "🤝", "💪", "🔥",
    "✨", "🎉", "😎", "👍", "🙌", "🤙", "💯", "⭐",
]


def resolve_consume_type(guard_level: int, source: str, collect_score: int = 0) -> str:
    """根据采集来源和守护等级描述消费类型。"""
    if guard_level == 3:
        return "总督"
    elif guard_level == 2:
        return "提督"
    elif guard_level == 1:
        return "舰长"
    elif source == "dahanghai":
        return "舰队"
    elif source == "gaonengbang":
        if collect_score > 10000:
            return "豪华礼物"
        elif collect_score > 1000:
            return "礼物"
        else:
            return "打榜"
    return "支持"


def pick_emoji() -> str:
    """随机选一个表情。"""
    return random.choice(EMOJIS)


def pick_template() -> str:
    """随机选一个模板。"""
    return random.choice(TEMPLATES)


def fill_template(
    template: str,
    target_nick: str = "",
    anchor_name: str = "",
    consume_type: str = "",
    emoji: str = "",
) -> str:
    """填充模板变量，生成最终消息。"""
    msg = template
    if "{target_nick}" in msg:
        msg = msg.replace("{target_nick}", target_nick or "朋友")
    if "{anchor_name}" in msg:
        msg = msg.replace("{anchor_name}", anchor_name or "这个主播")
    if "{consume_type}" in msg:
        msg = msg.replace("{consume_type}", consume_type or "支持")
    if "{emoji}" in msg:
        msg = msg.replace("{emoji}", emoji or pick_emoji())
    return msg


def _load_usage() -> dict:
    """加载模板使用记录。"""
    if not TEMPLATE_USAGE_FILE.exists():
        return {}
    try:
        with open(TEMPLATE_USAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_usage(usage: dict) -> None:
    """保存模板使用记录。"""
    TEMPLATE_USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TEMPLATE_USAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(usage, f, ensure_ascii=False, indent=2)


def _generate_greeting(
    uid: int,
    target_nick: str,
    anchor_name: str,
    guard_level: int,
    source: str,
    collect_score: int,
) -> str:
    """生成一条打招呼话术（带冷却去重）。"""
    usage = _load_usage()
    uid_key = str(uid)
    used_indices = set(usage.get(uid_key, []))

    # 找未用过的模板索引
    available = [i for i in range(len(TEMPLATES)) if i not in used_indices]

    if not available:
        # 全部用过了，清空冷却，重新开始
        logger.info("用户 %s 模板已全部用过，重置冷却", uid)
        used_indices.clear()
        available = list(range(len(TEMPLATES)))

    idx = random.choice(available)
    template = TEMPLATES[idx]

    consume_type = resolve_consume_type(guard_level, source, collect_score)
    emoji = pick_emoji()

    msg = fill_template(
        template,
        target_nick=target_nick,
        anchor_name=anchor_name,
        consume_type=consume_type,
        emoji=emoji,
    )

    # 记录使用
    used_indices.add(idx)
    usage[uid_key] = list(used_indices)
    _save_usage(usage)

    logger.debug("用户 %s 使用模板 #%d: %s", uid, idx, msg[:40])
    return msg


def generate_message(
    uid: int,
    target_nick: str = "",
    anchor_name: str = "",
    guard_level: int = 0,
    source: str = "",
    collect_score: int = 0,
) -> str:
    """
    为目标用户生成一条个性化消息。
    """
    return _generate_greeting(uid, target_nick, anchor_name, guard_level, source, collect_score)


def get_stats() -> dict:
    """获取模板使用统计。"""
    usage = _load_usage()
    return {
        "total_templates": len(TEMPLATES),
        "users_tracked": len(usage),
        "total_emojis": len(EMOJIS),
    }
