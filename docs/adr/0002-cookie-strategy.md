# ADR-0002: Cookie 策略——本机扫码 + 不跨机同步

## Status
Accepted (2026-06-08)

## Context
四平台都需要登录态才能拉到完整主页数据。约束：零成本、少人工干预、能在不同电脑上各自跑、不把凭据泄进 git。

## Decision
用 selenium 弹 Chromium 扫码登录，cookie 落本机 `cookies/<平台>.json`（已 gitignore）。换机器就各自重扫一次，**不做任何跨机同步**。cookie 过期由 `cookie_health` 从接口响应推断，status 面板提示「→ cli.py login <平台>」让人重扫。

## Consequences
- ＋ 实现最简，无需密钥管理 / 刷新 token / 云存储。
- ＋ 凭据永不离开本机，不进 git。
- － 多机部署要各扫一遍。
- － cookie 过期需人工重扫（但本就是给人扫码的工具，可接受）。

## Alternatives considered
- **git 同步 cookie**：凭据入库，泄露风险高，否决。
- **云 KV / refresh_token 自动续期**：要么有成本、要么各平台没有稳定的 web refresh 流程，复杂度不值当。详见 spec §1.1。
