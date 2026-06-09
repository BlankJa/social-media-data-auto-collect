# 新媒体信源采集 / Social Media Data Auto Collect

四平台（B 站 / 微博 / 抖音 / 快手）博主主页内容自动采集流水线。**纯接口 + 增量水位线 + Excel 渲染 + 跨平台自动调度**，替代手工 GUI 导出 + 按日期改名的工作流。

> **状态：早期开发中。** 当前已落地数据模型、cookie 存储、JSON 落盘 + 水位线、采集主循环。各平台具体接口、签名算法、登录扫码、Excel 渲染、调度模板尚未实现。进度详见 [docs/superpowers/plans/](docs/superpowers/plans/)。

---

## 为什么有这个项目

之前的工作流：靠某 GUI 工具在四个平台手动点击导出 Excel，按 `*-5.13.xlsx` / `*-5.14.xlsx` 这样手工命名归档，平台间靠人脑同步。命名风格不统一、容易漏、跨机器不可复现。

本项目把这套流程改成：
- 每天/每周本机自动跑（macOS launchd / Linux cron / Windows Task Scheduler）
- 直接打平台官方接口，原始响应落 JSON
- 从 JSON 渲染出**与现有命名风格保持一致**的 Excel（`B站UP主主页视频采集-YYYY.MM.DD.xlsx` 等）
- 增量逻辑用「文件存在 = 已采过」的天然水位线，断点续跑无状态

## 设计约束

| 约束 | 含义 |
|---|---|
| 免费 | 不接付费代理池、不上付费云函数 |
| 少人工干预 | 目标：每天自动跑、每周看一次状态。除了 cookie 重扫无日常操作 |
| 可移植 | `git clone` + `uv sync` + 每平台扫码一次就能跑；Windows / macOS / Linux 都支持 |
| Cookie 不跨机同步 | 换机器各扫一次，避免「cookie 入 git」的安全风险 |
| 不接第三方通知 | 不发邮件、不接 Bark / Server 酱；`cli.py status` 是唯一健康面板 |

## 架构

```
 配置 YAML        cookie JSON           平台子类                  数据树
┌──────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────────────┐
│ configs/ │    │  cookies/    │    │ Bilibili()  │    │ data/<plat>/         │
│  *.yaml  │───▶│  *.json      │───▶│ Douyin()    │───▶│   <account>/         │
└──────────┘    └──────────────┘    │ Weibo()     │    │     <post_id>.json   │
                                    │ Kuaishou()  │    │     _meta.json       │
                                    └─────────────┘    └──────────────────────┘
                                          │                       │
                                          │                       ▼
                                          │              ┌───────────────────┐
                                          │              │   rendering.py    │
                                          │              │   (列定义+xlsx)    │
                                          │              └────────┬──────────┘
                                          │                       ▼
                                          ▼              ┌───────────────────┐
                                  ┌──────────────┐       │ reports/          │
                                  │  status.json │       │   *-YYYY.MM.DD    │
                                  │ (健康面板)    │      │     .xlsx         │
                                  └──────────────┘       └───────────────────┘
```

四平台共用 `Platform` Protocol（`fetch_user_feed` / `parse` / `cookie_health`），具体接口、签名（B 站 `wbi` / 抖音 `X-Bogus`）按平台单独实现。共用 `collect_account` 循环负责增量水位线、节流、错误兜底。

## 平台支持

| 平台 | 接口 | 签名 | 登录 | Excel 列 | 状态 |
|---|---|---|---|---|---|
| B 站 | `/x/polymer/web-dynamic/v1/feed/space` | wbi | 扫码 | 9 列 | 🚧 计划中 (Phase 1) |
| 抖音 | `aweme/v1/web/aweme/post/` | X-Bogus | 扫码 | 待定 | 🚧 计划中 (Phase 2) |
| 微博 | `ajax/statuses/mymblog` | — | 扫码 | 待定 | 🚧 计划中 (Phase 3) |
| 快手 | GraphQL `visionProfilePhotoList` | — | 扫码 | 待定 | 🚧 计划中 (Phase 3) |

## 快速开始（计划中的工作流，部分尚未可用）

```bash
# 1. 克隆 + 装依赖（已可用）
git clone git@github.com:BlankJa/social-media-data-auto-collect.git
cd social-media-data-auto-collect
uv sync

# 2. 每平台扫码登录一次，cookie 落本机（计划 Task 8）
uv run python cli.py login bilibili
uv run python cli.py login weibo
uv run python cli.py login douyin
uv run python cli.py login kuaishou

# 3. 编辑账号清单（计划 Task 10）
$EDITOR configs/bilibili.yaml   # 写入要采的 mid + 备注

# 4. 跑增量采集（计划 Task 10）
uv run python cli.py collect all              # 四平台增量
uv run python cli.py collect bilibili --full  # 单平台全量

# 5. 渲染当日 Excel（计划 Task 10）
uv run python cli.py render all

# 6. 查看健康面板（计划 Task 16）
uv run python cli.py status
```

## 项目结构

```
.
├── cli.py                          # typer 入口（计划）
├── pyproject.toml                  # uv 项目定义
├── src/collector/
│   ├── schemas.py                  # ✅ Account / Post / RawPost / ColumnSpec
│   ├── cookies.py                  # ✅ 读写 + 年龄 + httpx 适配
│   ├── storage.py                  # ✅ JSON 文件树 + _meta.json + 原子写
│   ├── base.py                     # ✅ Platform Protocol + collect_account 循环
│   ├── signing/
│   │   ├── bilibili_wbi.py         # 🚧 B 站 wbi 签名
│   │   └── douyin_xbogus.py        # 🚧 抖音 X-Bogus
│   ├── bilibili.py / weibo.py /    # 🚧 各平台 fetch_user_feed + parse
│   │  douyin.py / kuaishou.py
│   ├── login/                      # 🚧 Selenium 扫码登录
│   ├── rendering.py                # 🚧 ColumnSpec → xlsx
│   ├── registry.py                 # 🚧 PLATFORMS 查表
│   └── status.py                   # 🚧 status.json + rich 终端面板
├── configs/                        # 🚧 账号清单 YAML（入 git）
├── cookies/                        # ⛔ 本机 cookie（gitignore）
├── data/                           # ⛔ 原始 JSON 树（gitignore）
├── reports/                        # ⛔ 渲染的 xlsx（gitignore）
├── infra/                          # 🚧 launchd / cron / Task Scheduler 模板
├── tests/                          # ✅ pytest，15 个测试已通过
└── docs/
    ├── adr/                        # 架构决策记录
    ├── superpowers/specs/          # 设计文档
    └── superpowers/plans/          # 19 任务实施计划
```

✅ = 已实现 · 🚧 = 待实现 · ⛔ = 运行时产出，不入 git

## 开发

### 依赖

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/) 管依赖
- Chrome / Chromium（登录扫码用）

### 装环境

```bash
uv sync                # 装运行时依赖
uv sync --extra dev    # 加上 pytest / pytest-cov
```

### 跑测试

```bash
uv run pytest tests/ -v
```

当前 15 个测试覆盖 `schemas` / `cookies` / `storage` / `base`，全过。

### 实施路线

- **Phase 1** (T1–T11)：基础架构 + B 站端到端 — 进行中（T1–T5 完成）
- **Phase 2** (T12–T13)：抖音 + X-Bogus
- **Phase 3** (T14–T15)：微博 + 快手
- **Phase 4** (T16–T19)：status 面板 + 调度模板 + 文档

完整 plan 见 `docs/superpowers/plans/2026-06-08-新媒体采集流水线.md`。

## 设计决策

- **平台抽象**：四平台共用 `Platform` Protocol，签名算法独立子模块
- **Cookie 不跨机**：换机器各扫一次，避免凭据入 git
- **不存历史指标**：每次跑会覆盖点赞/播放数；如需时序对比另起项目
- **Excel 列对齐手工命名**：保留现有 `*-YYYY.MM.DD.xlsx` 命名风格，便于和历史归档无缝衔接

后续会在 `docs/adr/` 下沉淀决策记录。

## License

待定。

## 致谢

B 站 wbi 签名算法参考 [SocialSisterYi/bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect)。
