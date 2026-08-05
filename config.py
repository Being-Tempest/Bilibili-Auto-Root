"""
Bili Audience Insight · 配置文件（学习版）

免责声明：
  本项目仅供学习 B站开放数据与 bilibili-api 用法。
  使用本工具请遵守 B站社区规范，只与自己账号认识的对象交流，
  不群发、不骚扰。本文件不包含任何真实凭证。

凭据说明：
  发送私信需要你自己的 Cookie，放到仓库根目录的 credentials.json：
    {"sessdata": "xxx", "bili_jct": "xxx", "buvid3": "xxx"}
  不配置也能运行 collect / filter（这两个只用公开接口）。
"""

import json
import os
from pathlib import Path
from typing import Optional

# ============================================================
# 凭据（默认不配置，走 credentials.json / 环境变量）
# ============================================================

def get_credential():
    """
    加载 B站 API 凭据。

    优先级：
      1. credentials.json（从浏览器 Cookie 导出）
      2. 环境变量 BILI_SESSDATA / BILI_BILI_JCT / BILI_BUVID3

    未配置时返回 None——collect / filter 的公开接口仍可用，
    只有 send（私信）需要凭据。
    """
    from bilibili_api import Credential  # lazy import

    if CREDENTIALS_FILE.exists():
        try:
            with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            sessdata = saved.get("sessdata", "") or saved.get("SESSDATA", "")
            bili_jct = saved.get("bili_jct", "") or saved.get("bili_jct", "")
            buvid3 = saved.get("buvid3", "") or saved.get("BUVID3", "")
            if sessdata and bili_jct:
                return Credential(sessdata=sessdata, bili_jct=bili_jct, buvid3=buvid3 or "")
        except Exception:
            pass

    sessdata = os.environ.get("BILI_SESSDATA", "")
    bili_jct = os.environ.get("BILI_BILI_JCT", "")
    if sessdata and bili_jct:
        return Credential(
            sessdata=sessdata,
            bili_jct=bili_jct,
            buvid3=os.environ.get("BILI_BUVID3", ""),
        )
    return None

# ============================================================
# 目标采集
# ============================================================

# 要观察的直播间 ID（改成你自己的目标直播间）
TARGET_ROOM_IDS: list[int] = []

# 每个直播间最多抓取的送礼用户数
MAX_USERS_PER_ROOM = 50

# ============================================================
# 用户筛选阈值（理解"什么样的用户值得认识"）
# ============================================================

MIN_LEVEL = 3            # 用户等级 ≥ 3
REQUIRE_VIP = True       # 必须有大会员
REQUIRE_AVATAR = True    # 必须有自定义头像
REQUIRE_SIGN = False     # 不强制有个性签名
MIN_VIDEO_COUNT = 0      # 不强制有投稿

# ============================================================
# 话术冷却
# 对同一位用户不重复使用同一模板，避免单调
# ============================================================

TEMPLATE_COOLDOWN_DAYS = 7

# 私信长度上限（B站约 200 字）
MAX_MSG_LEN = 200

# ============================================================
# 路径
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TARGETS_POOL_FILE = DATA_DIR / "targets_pool.json"
SENT_LOG_FILE = DATA_DIR / "sent_log.json"
BLACKLIST_FILE = DATA_DIR / "blacklist.json"

# 确保 data 目录存在
DATA_DIR.mkdir(exist_ok=True)

# ============================================================
# 日志
# ============================================================

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_LEVEL = "INFO"
