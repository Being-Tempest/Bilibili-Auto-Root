"""
主控编排（学习版）。

流水线：采集公开榜单 → 硬规则筛选 → 查看合格池 → 单条发送示例。

本版刻意不提供"批量群发"能力。工具的角色是帮助你理解你的观众
（谁在消费、谁活跃），然后一次一个、克制地建立连接。

用法：
  python orchestrator.py collect         — 采集榜单用户
  python orchestrator.py filter          — 硬规则筛选
  python orchestrator.py run             — 采集 + 筛选
  python orchestrator.py status          — 查看状态与数据文件
  python orchestrator.py send <uid>      — 向指定用户发送一条私信（示例）
"""

import logging
import sys
from pathlib import Path

from config import DATA_DIR, CREDENTIALS_FILE

logger = logging.getLogger(__name__)


def step_collect(room_ids: list[int] | None = None):
    """Step 1: 采集目标用户。"""
    from collector import run_collect
    logger.info("=" * 50)
    logger.info("Step 1: 目标采集")
    logger.info("=" * 50)
    users = run_collect(room_ids)
    logger.info("采集完成，共 %d 个用户写入 targets_pool.json", len(users))


def step_filter(limit: int | None = None):
    """Step 2: 筛选用户。"""
    from filter import run_filter
    logger.info("=" * 50)
    logger.info("Step 2: 用户筛选")
    logger.info("=" * 50)
    passed, rejected = run_filter(limit)
    logger.info("筛选完成，通过 %d 人，拒绝 %d 人", len(passed), len(rejected))


def step_send(uid: int, message: str | None = None):
    """Step 3: 向单个用户发送一条私信（示例）。"""
    from sender import demo_send
    logger.info("=" * 50)
    logger.info("Step 3: 单条私信示例")
    logger.info("=" * 50)
    demo_send(uid, message)


def step_status():
    """显示当前状态与数据文件。"""
    from sender import get_today_stats

    print("=" * 50)
    print("Bili Audience Insight · 状态")
    print("=" * 50)

    cred_ok = CREDENTIALS_FILE.exists()
    print(f"  凭据: {'已配置 (credentials.json)' if cred_ok else '未配置（send 需要，collect/filter 不需要）'}")

    stats = get_today_stats()
    print(f"  今日发送: {stats['sent']} 成功 / {stats['failed']} 失败")

    files = {
        "targets_pool.json": DATA_DIR / "targets_pool.json",
        "filtered_pool.json": DATA_DIR / "filtered_pool.json",
        "sent_log.json": DATA_DIR / "sent_log.json",
    }
    print()
    print("  数据文件:")
    for name, path in files.items():
        size = path.stat().st_size if path.exists() else 0
        status = f"{size:,} bytes" if path.exists() else "X 不存在"
        print(f"    {name:25s} {status}")


def run_all():
    """执行全流程：采集 → 筛选（不含自动发送）。"""
    step_collect()
    print()
    step_filter()
    print()
    print("合格目标已写入 data/filtered_pool.json。")
    print("发送请手动执行：python orchestrator.py send <uid>")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == "collect":
        step_collect()
    elif cmd == "filter":
        step_filter()
    elif cmd == "run":
        run_all()
    elif cmd == "status":
        step_status()
    elif cmd == "send" and len(sys.argv) >= 3:
        uid = int(sys.argv[2])
        msg = sys.argv[3] if len(sys.argv) > 3 else None
        step_send(uid, msg)
    else:
        print(f"未知命令: {cmd}")
        print("可用: collect | filter | run | status | send <uid>")


if __name__ == "__main__":
    main()
