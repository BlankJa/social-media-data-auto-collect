# 域语言（Domain Language）

本项目的核心术语。改代码、命名、写文档时以此为准。

- **账号 (account)**：一个平台上的博主主体，由 `(platform, account_id)` 唯一标识。`account_id` 各平台含义不同：B 站是 mid、抖音是 sec_uid、微博是数字 uid、快手是主页 URL 末段。
- **内容 / Post**：账号在该平台上发布的一条视频或博文，由 `(platform, post_id)` 唯一标识。
- **采集 (collect)**：一次 `cli.py collect <平台>` 的执行；分增量或全量（`--full`）。
- **水位线 (`_meta.newest_post_id`)**：上次成功采集到的最新 post_id；增量循环从最新往回拉，遇到它就停。落盘的「文件已存在 = 已采过」是天然的去重水位线。
- **Cookie 健康度 (cookie_health)**：`ok / warning / expired` 三态，由最近一次接口响应（`self.last_response`）推断。各平台读各自的响应级字段：B 站 `code`、微博 `ok`、抖音 `status_code`、快手 `result`。
- **采集副产品 (artifact)**：`reports/*.xlsx` 是从 `data/` 渲染出来的，可随时重生成，不是源数据。
- **平台 (Platform)**：实现 `fetch_user_feed` / `parse` / `cookie_health` 的子类（Bilibili / Douyin / Weibo / Kuaishou），共用 `collect_account` 循环。

## 架构决策

详见 [`docs/adr/`](docs/adr/)：

- **ADR-0001** 平台抽象：为什么 `Platform` Protocol + 四子类，而不是四个独立脚本。
- **ADR-0002** Cookie 策略：为什么 selenium 扫码 + 本机存，而不是 refresh_token / 云同步。
- **ADR-0003** 不保留历史指标：覆盖写的 trade-off，将来要加时序的最低成本路径。
- **ADR-0004** Excel 列保真：为什么沿用旧表头（含工具痕迹列），将来要重构列序的标准动作。
