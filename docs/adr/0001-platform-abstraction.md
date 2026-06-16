# ADR-0001: 平台抽象——Platform Protocol + 四子类

## Status
Accepted (2026-06-08)

## Context
四个平台（B 站 / 微博 / 抖音 / 快手）的接口端点、签名算法、字段命名、计数格式差异极大，但**采集流程完全相同**：拉主页 feed → 解析成统一 Post → 增量遇水位线即停 → 落 JSON → 渲染 Excel。

## Decision
定义 `Platform` Protocol（`fetch_user_feed` / `parse` / `cookie_health` + `last_response`），每平台一个子类只管「接口差异」；把「流程共性」（增量水位线、节流退避、错误兜底、落盘）收进共用的 `collect_account` 循环。签名算法（B 站 wbi、抖音 a_bogus）再下沉到 `signing/` 独立子模块。

## Consequences
- ＋ 新增平台只写一个 fetch+parse+列定义，不碰主循环。
- ＋ 某平台接口/签名升级，局部重写不连累其他平台（已在快手真机返工中验证：只改了 `kuaishou.py` 的 query 和 parse）。
- － Protocol 的契约（如 `last_response` 由谁写）是隐性约定，需文档约束。

## Alternatives considered
- **四个独立脚本**：每个平台各自重写水位线 / 重试 / 落盘逻辑。放弃——共性代码四份拷贝，改一处要改四处，且增量语义容易跑偏。
