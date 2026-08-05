# Bili Auto Root · B站写作业（学习版）

一个帮助你写作业的学习项目：用公开接口采集榜单、按硬规则筛选出活跃消费用户、生成一段克制的打招呼话术，并演示如何用 `bilibili-api` 发送一条私信。

> **这不是群发工具。** 本仓库刻意不包含批量循环、速率对抗、多账号等能力。
> 工具的价值在于「了解你的观众」；发送只演示单条、克制的私信。

## 设计原则

1. **只用公开数据**：只调用 B站公开接口（直播间贡献榜、大航海榜、用户空间资料）。
2. **克制发送**：一次只给一个人发一条，不轰炸、不群发。
3. **尊重用户**：筛选规则偏向「真实、活跃、有消费意愿」的用户，避开沉默/风险账号。
4. **可审计**：所有发送都记录到 `data/sent_log.json`。

## 快速开始

### 1. 安装

```bash
pip install -r requirements.txt
```

### 2. 配置目标直播间

编辑 `config.py`，把 `TARGET_ROOM_IDS` 改成你想观察的直播间 ID。

### 3. 采集榜单用户（公开接口，无需登录）

```bash
python orchestrator.py collect
```

### 4. 硬规则筛选

```bash
python orchestrator.py filter
```

筛选结果（含评分与拒绝原因）写入 `data/filtered_pool.json`。

### 5. （可选）演示发送一条私信

发送需要你自己的 Cookie。在仓库根目录创建 `credentials.json`（不要提交到版本控制）：

```json
{"sessdata": "...", "bili_jct": "...", "buvid3": "..."}
```

然后发送一条：

```bash
python orchestrator.py send <目标UID>
```

只发送**一条**，之后由你自己判断是否继续。

## 文件结构

```
├── config.py         # 配置：目标直播间、筛选阈值、路径
├── collector.py      # 采集：公开榜单 → 候选池
├── filter.py         # 筛选：硬规则打分 → 合格池
├── templates.py      # 话术模板：变量替换 + 冷却去重
├── sender.py         # 单条私信发送示例
├── orchestrator.py   # 主控：collect / filter / run / status / send
├── requirements.txt  # 依赖（仅 bilibili-api）
└── data/             # 运行时数据（已 gitignore）
```

## 免责声明

- 本项目仅供学习 Python、`bilibili-api` 与 B站开放数据接口。
- 请遵守 B站社区规范与你所在地区的法律法规。
- 只使用你自己的账号，不群发、不骚扰、不用于任何商业灰产。
- 作者不对任何使用方式造成的后果负责。

## License

MIT
