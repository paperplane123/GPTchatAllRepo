#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash -n "${SCRIPT_DIR}/install.sh"
bash -n "${SCRIPT_DIR}/uninstall.sh"

grep -q 'on open droppedItems' "${SCRIPT_DIR}/readonly-viewer.applescript"
grep -q '/usr/bin/qlmanage -p' "${SCRIPT_DIR}/readonly-viewer.applescript"
grep -q 'CFBundleTypeRole string Viewer' "${SCRIPT_DIR}/install.sh"
grep -q 'CFBundleDocumentTypes' "${SCRIPT_DIR}/install.sh"

if grep -R -nE 'rm -rf "?\$\{?HOME\}?"?$|sudo ' "${SCRIPT_DIR}" --exclude=test.sh; then
  echo "检测到不允许的高风险安装命令。" >&2
  exit 1
fi

echo "macOS 文档只读查看器静态校验通过。"
