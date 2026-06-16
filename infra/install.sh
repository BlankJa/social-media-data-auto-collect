#!/usr/bin/env bash
# 安装定时调度：macOS 用 launchd，Linux 用 crontab。Windows 见 install.ps1。
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$REPO/logs"

case "$(uname -s)" in
  Darwin)
    PLISTS=("com.fudan.collector.daily" "com.fudan.collector.weekly")
    mkdir -p "$HOME/Library/LaunchAgents"
    for n in "${PLISTS[@]}"; do
      out="$HOME/Library/LaunchAgents/$n.plist"
      sed "s|__REPO__|$REPO|g" "$REPO/infra/$n.plist" > "$out"
      launchctl unload "$out" 2>/dev/null || true
      launchctl load "$out"
      echo "✓ loaded $out"
    done
    ;;
  Linux)
    out="$REPO/infra/.collector.cron.expanded"
    sed "s|__REPO__|$REPO|g" "$REPO/infra/collector.cron" > "$out"
    # 先剔除旧的 fudan-collector 行再追加，幂等
    ( crontab -l 2>/dev/null | grep -v "fudan-collector"; cat "$out"; ) | crontab -
    echo "✓ crontab installed"
    ;;
  *)
    echo "unsupported OS, use install.ps1 on Windows"
    exit 1
    ;;
esac
