"""
用户筛选模块（学习版）。

读取 data/targets_pool.json，逐用户查资料（公开接口），硬规则打分筛选：
  - 必须有大会员（vip.status > 0）
  - 等级 ≥ MIN_LEVEL（默认3）
  - 非封禁/静默状态（silence == 0）
  - 有自定义头像（非默认头像）

输出合格目标池，写入 data/targets_pool.json（覆盖）和 data/filtered_pool.json。

筛选的意义：与其广撒网，不如把精力留给"真实、活跃、有消费意愿"的用户。
"""

import json
import time
import logging
from typing import Optional

from bilibili_api import sync
from bilibili_api.user import User

from config import (
    get_credential,
    MIN_LEVEL,
    REQUIRE_VIP,
    REQUIRE_AVATAR,
    DATA_DIR,
    TARGETS_POOL_FILE,
)

logger = logging.getLogger(__name__)

FILTERED_POOL_FILE = DATA_DIR / "filtered_pool.json"


def _is_default_avatar(face_url: str) -> bool:
    """判断是否为 B站默认头像（无自定义头像）。"""
    if not face_url:
        return True
    # B站默认头像通常不含用户专属 hash
    default_patterns = ["noface", "default"]
    url_lower = face_url.lower()
    return any(p in url_lower for p in default_patterns)


def fetch_user_info(uid: int, credential=None, retries: int = 3) -> Optional[dict]:
    """
    获取用户空间信息，带 -799 限流重试。

    Returns:
        dict 或 None（获取失败时）
    """
    from bilibili_api.exceptions import ResponseCodeException

    for attempt in range(retries):
        try:
            user = User(uid, credential=credential)
            return sync(user.get_user_info())
        except ResponseCodeException as e:
            if e.code == -799:
                wait = (attempt + 1) * 3  # 3s, 6s, 9s 退避
                logger.debug("用户 %s 触发限流，等待 %ds 重试 (%d/%d)", uid, wait, attempt + 1, retries)
                time.sleep(wait)
            else:
                logger.warning("获取用户 %s 信息失败 (code=%s): %s", uid, e.code, e.msg)
                return None
        except Exception as e:
            logger.warning("获取用户 %s 信息失败: %s", uid, e)
            return None

    logger.warning("获取用户 %s 信息失败: 重试 %d 次后仍限流", uid, retries)
    return None


def evaluate_user(raw: dict) -> tuple[bool, int, dict]:
    """
    硬规则评分，返回 (是否通过, 分数, 摘要)。

    打分逻辑（满分 10）：
      - 有大会员: +3
      - 等级≥5: +2, 等级≥3: +1
      - 有自定义头像: +1
      - 有签名: +1
      - 有粉丝勋章: +1
      - 非风险账号: +1
      - 有直播信息: +1
    """
    score = 0
    reasons: list[str] = []
    fail_reasons: list[str] = []

    # --- 硬性一票否决 ---
    silence = raw.get("silence", 0)
    if silence != 0:
        fail_reasons.append(f"账号被静默/封禁 (silence={silence})")

    # --- 大会员 ---
    vip = raw.get("vip", {})
    vip_status = vip.get("status", 0) if isinstance(vip, dict) else 0
    if REQUIRE_VIP and vip_status == 0:
        fail_reasons.append("无大会员")
    else:
        score += 3

    # --- 等级 ---
    level = raw.get("level", 0)
    if level < MIN_LEVEL:
        fail_reasons.append(f"等级过低 (level={level}, need≥{MIN_LEVEL})")
    if level >= 5:
        score += 2
    elif level >= 3:
        score += 1

    # --- 头像 ---
    face = raw.get("face", "")
    if REQUIRE_AVATAR and _is_default_avatar(face):
        fail_reasons.append("默认头像")
    else:
        if face:
            score += 1

    # --- 加分项 ---
    if raw.get("sign", ""):
        score += 1

    fans_medal = raw.get("fans_medal", {})
    if isinstance(fans_medal, dict) and fans_medal.get("show"):
        score += 1

    if not raw.get("is_risk", True):
        score += 1

    if raw.get("live_room"):
        score += 1

    # --- 结果 ---
    passed = len(fail_reasons) == 0

    summary = {
        "uid": raw.get("mid"),
        "name": raw.get("name", ""),
        "level": level,
        "vip": vip_status,
        "face": face[:80] if face else "",
        "sign": raw.get("sign", "")[:50],
        "score": score,
    }

    if not passed:
        summary["reject_reason"] = "; ".join(fail_reasons)

    return passed, score, summary


def load_targets() -> list[dict]:
    """从 targets_pool.json 读取待筛选用户。"""
    if not TARGETS_POOL_FILE.exists():
        logger.warning("targets_pool.json 不存在，请先运行 collector.py")
        return []
    with open(TARGETS_POOL_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_filtered(passed: list[dict], rejected: list[dict]) -> None:
    """
    保存筛选结果。
    - filtered_pool.json：通过筛选的合格目标
    - 同时更新 targets_pool.json 为只含通过的用户
    """
    FILTERED_POOL_FILE.parent.mkdir(parents=True, exist_ok=True)

    # 合格目标
    with open(FILTERED_POOL_FILE, "w", encoding="utf-8") as f:
        json.dump(passed, f, ensure_ascii=False, indent=2)

    logger.info(
        "筛选完成: 通过 %d / 拒绝 %d / 总计 %d",
        len(passed), len(rejected), len(passed) + len(rejected),
    )


def run_filter(limit: Optional[int] = None) -> tuple[list[dict], list[dict]]:
    """
    执行全量筛选。

    Args:
        limit: 最多筛选 N 个用户（用于测试），None 表示全部。

    Returns:
        (passed, rejected) 两个列表。
    """
    raw_targets = load_targets()
    if not raw_targets:
        return [], []

    credential = get_credential()
    passed: list[dict] = []
    rejected: list[dict] = []

    targets = raw_targets[:limit] if limit else raw_targets

    for i, target in enumerate(targets):
        uid = target.get("uid")
        if not uid:
            continue

        logger.info("筛选 [%d/%d] uid=%s", i + 1, len(targets), uid)

        info = fetch_user_info(int(uid), credential)
        if info is None:
            summary = {
                "uid": uid,
                "name": target.get("uname", ""),
                "reject_reason": "API 获取失败",
                "source": target.get("source", ""),
            }
            rejected.append(summary)
            continue

        ok, score, summary = evaluate_user(info)
        summary["source"] = target.get("source", "")
        summary["collect_score"] = target.get("score", 0)
        summary["guard_level"] = target.get("guard_level", 0)

        if ok:
            passed.append(summary)
            logger.info("  ✓ 通过 (score=%d, level=%d, vip=%s)", score, summary["level"], summary["vip"])
        else:
            rejected.append(summary)
            logger.info("  ✗ 拒绝: %s", summary.get("reject_reason", ""))

        time.sleep(1.5)  # 查资料间隔，礼貌请求

    # 按分数降序排列
    passed.sort(key=lambda u: u["score"], reverse=True)
    save_filtered(passed, rejected)
    return passed, rejected


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_filter()
