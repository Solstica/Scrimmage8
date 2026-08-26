#!/usr/bin/env bash
set -Eeuo pipefail

# Git Bash / macOS / Linux compatibility wrapper.
# 可从任意当前目录启动；实际入口固定使用本脚本同目录下的 preview_latest.py。

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if command -v python >/dev/null 2>&1; then
  PY=(python)
elif command -v python3 >/dev/null 2>&1; then
  PY=(python3)
else
  echo "[FAIL] 未找到 python/python3。"
  exit 2
fi

exec "${PY[@]}" "$SCRIPT_DIR/preview_latest.py" --fast "$@"
