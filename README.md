# 新媒体信源采集 / Social Media Data Auto Collect

四平台（B 站 / 微博 / 抖音 / 快手）博主主页内容自动采集流水线。**纯接口 + 增量水位线 + Excel 渲染 + 跨平台自动调度**，替代手工 GUI 导出 + 按日期改名的工作流。

> **状态：第一期已交付。** 四平台（B 站 / 微博 / 抖音 / 快手）全链路打通并经真机验证，登录扫码、增量采集、Excel 渲染、status 健康面板、跨平台调度模板均已实现，35 个测试全过。进度详见 [docs/superpowers/plans/](docs/superpowers/plans/)。

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

四平台共用 `Platform` Protocol（`fetch_user_feed` / `parse` / `cookie_health`），具体接口、签名（B 站 `wbi` / 抖音 `a_bogus`）按平台单独实现。共用 `collect_account` 循环负责增量水位线、节流、错误兜底。

## 平台支持

| 平台 | 接口 | 签名 | 登录 | Excel 列 | 状态 |
|---|---|---|---|---|---|
| B 站 | `/x/polymer/web-dynamic/v1/feed/space` | wbi | 扫码 | 9 列 | ✅ 真机验证通过 |
| 抖音 | `aweme/v1/web/aweme/post/` | a_bogus | 扫码 | 13 列 | ✅ 真机验证通过 |
| 微博 | `ajax/statuses/mymblog` | — | 扫码 | 10 列 | ✅ 真机验证通过 |
| 快手 | GraphQL `visionProfilePhotoList` | — | 扫码 | 8 列 | ✅ 真机验证通过 |

> 抖音签名：计划里的 X-Bogus 已于 2024-06 被弃用，现用 **a_bogus**（封装 [f2](https://github.com/Johnserf-Seed/f2) 库，非自研，含时间因子不可确定复现）。

## 快速开始

```bash
# 1. 克隆 + 装依赖
git clone git@github.com:BlankJa/social-media-data-auto-collect.git
cd social-media-data-auto-collect
uv sync

# 2. 每平台扫码登录一次，cookie 落本机 cookies/<平台>.json
uv run python cli.py login bilibili
uv run python cli.py login weibo
uv run python cli.py login douyin
uv run python cli.py login kuaishou

# 3. 加账号（免编 YAML）——交互式或带参，详见下方「账号管理」
uv run python cli.py account add              # 交互式选平台、输 id/名称
uv run python cli.py account import 账号.xlsx  # 批量导入

# 4. 跑采集
uv run python cli.py collect all              # 四平台增量
uv run python cli.py collect bilibili --full  # 单平台全量

# 5. 渲染当日 Excel 到 reports/
uv run python cli.py render all

# 6. 查看健康面板（cookie 年龄 + 建议哪个该重扫）
uv run python cli.py status

# 7. 装定时调度（一次性）
bash infra/install.sh                                # macOS / Linux
powershell -ExecutionPolicy Bypass -File infra\install.ps1   # Windows
```

## 账号管理（`cli.py account`）

不用手编 YAML，增删查与批量导入账号：

```bash
uv run python cli.py account list                          # 列出四平台所有账号
uv run python cli.py account add                           # 交互式：选平台 → 输 id → 输名称
uv run python cli.py account add kuaishou 3xabc 复旦大学    # 带参直接加
uv run python cli.py account remove                        # 交互式：选平台 → 选要删的账号
uv run python cli.py account template 账号.xlsx            # 生成空导入模板
uv run python cli.py account import 账号.xlsx             # 批量导入（.xlsx 或 .csv）
```

- **导入文件**三列：`platform` / `account_id` / `account_name`（首行表头）。`platform` 填 `bilibili`/`weibo`/`douyin`/`kuaishou`。
- 自动**去重**（同 account_id 跳过），并汇总 `新增 N · 跳过 M · 无效 K`。
- 对 `account_id` 做格式提示（如快手该 `3x` 开头、抖音该 `MS4w` 开头）——**仅警告不拦截**。
- 导入后直接 `collect`：新账号无水位线，会被自动当**全量首采**，之后转增量。

## 健康面板（`cli.py status`）

```
               新媒体采集状态
┏━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┓
┃ 平台     ┃ Cookie 年龄 ┃ 近7天 ┃ 建议    ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━┩
│ bilibili │ 3天         │ 12    │ ✅ 正常 │
│ kuaishou │ 6天         │ 0     │ ⚠️ 快过期，建议重扫 │
│ weibo    │ —           │ 0     │ ❌ 未登录，需扫码   │
└──────────┴─────────────┴───────┴─────────┘
```

「Cookie 年龄」实时从 cookie 文件算（不依赖上次运行），所以没跑过采集也能看出谁该重扫。**快手是 7 天免登录会话，约每周过期一次**，满 6 天即提示；其余平台 25 天阈值。

## 项目结构

```
.
├── cli.py                          # ✅ typer 入口：login / collect / render / status / account
├── pyproject.toml                  # uv 项目定义
├── src/collector/
│   ├── schemas.py                  # ✅ Account / Post / RawPost / ColumnSpec
│   ├── accounts.py                 # ✅ 账号增删查 + csv/xlsx 导入（cli.py account 后端）
│   ├── cookies.py                  # ✅ 读写 + 年龄 + httpx 适配
│   ├── storage.py                  # ✅ JSON 文件树 + _meta.json + 原子写
│   ├── base.py                     # ✅ Platform Protocol + collect_account 循环
│   ├── signing/
│   │   ├── bilibili_wbi.py         # ✅ B 站 wbi 签名
│   │   └── douyin_abogus.py        # ✅ 抖音 a_bogus（封装 f2）
│   ├── bilibili.py / weibo.py /    # ✅ 各平台 fetch_user_feed + parse
│   │  douyin.py / kuaishou.py
│   ├── login/                      # ✅ Selenium 扫码登录
│   ├── rendering.py                # ✅ ColumnSpec → xlsx
│   ├── registry.py                 # ✅ PLATFORMS 查表
│   └── status.py                   # ✅ status.json + rich 终端面板
├── configs/                        # ✅ 账号清单 YAML（入 git）
├── cookies/                        # ⛔ 本机 cookie（gitignore）
├── data/                           # ⛔ 原始 JSON 树（gitignore）
├── reports/                        # ⛔ 渲染的 xlsx（gitignore）
├── infra/                          # ✅ launchd / cron / Task Scheduler 模板
├── tests/                          # ✅ pytest，35 个测试已通过
└── docs/
    ├── adr/                        # ✅ 4 个架构决策记录
    ├── superpowers/specs/          # 设计文档
    └── superpowers/plans/          # 19 任务实施计划
```

✅ = 已实现 · ⛔ = 运行时产出，不入 git

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

当前 35 个测试覆盖 `schemas` / `cookies` / `storage` / `base` / 四平台 parser / 列定义 / status，全过。

### 实施路线（已全部完成）

- **Phase 1** (T1–T11)：基础架构 + B 站端到端 ✅
- **Phase 2** (T12–T13)：抖音 + a_bogus ✅
- **Phase 3** (T14–T15)：微博 + 快手 ✅
- **Phase 4** (T16–T19)：status 面板 + 调度模板 + 文档 ✅

完整 plan 见 `docs/superpowers/plans/2026-06-08-新媒体采集流水线.md`。

## 设计决策

- **平台抽象**：四平台共用 `Platform` Protocol，签名算法独立子模块
- **Cookie 不跨机**：换机器各扫一次，避免凭据入 git
- **不存历史指标**：每次跑会覆盖点赞/播放数；如需时序对比另起项目
- **Excel 列对齐手工命名**：保留现有 `*-YYYY.MM.DD.xlsx` 命名风格，便于和历史归档无缝衔接

详细决策记录见 [`docs/adr/`](docs/adr/)（ADR-0001 平台抽象 / 0002 Cookie 策略 / 0003 不保留历史指标 / 0004 Excel 列保真）。

## License

待定。

## 致谢

B 站 wbi 签名算法参考 [SocialSisterYi/bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect)。
