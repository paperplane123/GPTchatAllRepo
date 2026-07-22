#!/bin/bash
set -euo pipefail

PLUGIN_NAME="WPS_MAC_READER"
ADDON_ROOT="${HOME}/Library/Containers/com.kingsoft.wpsoffice.mac/Data/.kingsoft/wps/jsaddons"
PUBLISH_FILE="${ADDON_ROOT}/publish.xml"

if [[ -f "${PUBLISH_FILE}" ]]; then
  BACKUP_FILE="${PUBLISH_FILE}.bak.$(date +%Y%m%d%H%M%S)"
  cp "${PUBLISH_FILE}" "${BACKUP_FILE}"
  perl -0pi -e 's/\s*<jsplugin(?:online)?\b[^>]*\bname="WPS_MAC_READER"[^>]*\/>//g' "${PUBLISH_FILE}"
  echo "已从 publish.xml 移除插件配置。备份：${BACKUP_FILE}"
fi

REMOVED=0
shopt -s nullglob
for DEST_DIR in "${ADDON_ROOT}/${PLUGIN_NAME}_"*; do
  if [[ -d "${DEST_DIR}" ]]; then
    rm -rf "${DEST_DIR}"
    echo "已删除插件目录：${DEST_DIR}"
    REMOVED=1
  fi
done
shopt -u nullglob

if [[ "${REMOVED}" -eq 0 ]]; then
  echo "未发现 ${PLUGIN_NAME} 插件目录。"
fi

echo "卸载完成。请完全退出并重新打开 WPS。"
