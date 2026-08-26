#!/usr/bin/env bash
set -Eeuo pipefail

# One-command latest paper preview for Git Bash / macOS / Linux.
# Run from the stable repository root. The script never merges/rebases the caller branch.

ROOT="${CUMCM_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || true)}"
if [[ -z "$ROOT" || ( ! -d "$ROOT/.git" && ! -f "$ROOT/.git" ) ]]; then
  echo "[FAIL] 请在比赛仓库根目录运行，或设置 CUMCM_ROOT。"
  exit 2
fi

NAME="$(basename "$ROOT")"
CTRL="${CUMCM_PREVIEW_CTRL:-$(dirname "$ROOT")/${NAME}-preview-controller}"
PREVIEW="${CUMCM_PREVIEW_DIR:-$(dirname "$ROOT")/${NAME}-paper-preview}"

cleanup_ctrl() {
  cd "$ROOT" 2>/dev/null || true
  git worktree remove --force "$CTRL" >/dev/null 2>&1 || true
  rm -rf "$CTRL" >/dev/null 2>&1 || true
  git worktree prune --expire now >/dev/null 2>&1 || true
}
trap cleanup_ctrl EXIT

cd "$ROOT"

echo "[1/5] 更新远端引用"
git fetch origin --prune

echo "[2/5] 清理旧临时 worktree"
git worktree prune --expire now >/dev/null 2>&1 || true
git worktree remove --force "$CTRL" >/dev/null 2>&1 || true
git worktree remove --force "$PREVIEW" >/dev/null 2>&1 || true
rm -rf "$CTRL" "$PREVIEW"
git worktree prune --expire now >/dev/null 2>&1 || true

echo "[3/5] 建立最新版 preview controller"
git worktree add --force --detach "$CTRL" origin/feature/shared >/dev/null

cd "$CTRL"
echo "[4/5] 临时拼装各责任分支并编译"
python scripts/preview_fast.py \
  --preview-dir "$PREVIEW" \
  --base-branch feature/paper-shell \
  --strict \
  --strict-preflight \
  --no-open

echo "[5/5] 完成"
PDF="$PREVIEW/paper/main.pdf"
if [[ -f "$PDF" ]]; then
  echo "PDF: $PDF"
  if command -v explorer.exe >/dev/null 2>&1 && command -v cygpath >/dev/null 2>&1; then
    explorer.exe "$(cygpath -w "$PDF")" >/dev/null 2>&1 || true
  elif command -v open >/dev/null 2>&1; then
    open "$PDF" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$PDF" >/dev/null 2>&1 || true
  fi
else
  echo "[WARN] 未生成 main.pdf，请查看上方第一处硬错误。"
fi
