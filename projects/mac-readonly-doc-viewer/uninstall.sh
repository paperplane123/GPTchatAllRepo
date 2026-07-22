#!/bin/bash
set -euo pipefail

APP_PATH="${HOME}/Applications/文档只读阅读.app"
LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"

if [[ -x "${LSREGISTER}" && -d "${APP_PATH}" ]]; then
  "${LSREGISTER}" -u "${APP_PATH}" >/dev/null 2>&1 || true
fi

if [[ -d "${APP_PATH}" ]]; then
  rm -rf "${APP_PATH}"
  echo "已卸载：${APP_PATH}"
else
  echo "未发现已安装的查看器：${APP_PATH}"
fi
