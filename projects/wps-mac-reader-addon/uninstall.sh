#!/bin/bash
set -euo pipefail

PLUGIN_NAME="WPS_MAC_READER"
PLUGIN_VERSION="0.1.0"
PLUGIN_FOLDER="${PLUGIN_NAME}_${PLUGIN_VERSION}"
ADDON_ROOT="${HOME}/Library/Containers/com.kingsoft.wpsoffice.mac/Data/.kingsoft/wps/jsaddons"
DEST_DIR="${ADDON_ROOT}/${PLUGIN_FOLDER}"
PUBLISH_FILE="${ADDON_ROOT}/publish.xml"

if [[ -f "${PUBLISH_FILE}" ]]; then
  BACKUP_FILE="${PUBLISH_FILE}.bak.$(date +%Y%m%d%H%M%S)"
  cp "${PUBLISH_FILE}" "${BACKUP_FILE}"
  perl -0pi -e 's/\s*<jsplugin(?:online)?\b[^>]*\bname="WPS_MAC_READER"[^>]*\/>//g' "${PUBLISH_FILE}"
  echo "已从 publish.xml 移除插件配置。备份：${BACKUP_FILE}"
fi

if [[ -d "${DEST_DIR}" ]]; then
  rm -rf "${DEST_DIR}"
  echo "已删除插件目录：${DEST_DIR}"
else
  echo "未发现插件目录：${DEST_DIR}"
fi

echo "卸载完成。请完全退出并重新打开 WPS。"
