#!/bin/bash
set -euo pipefail

PLUGIN_NAME="WPS_MAC_READER"
PLUGIN_VERSION="0.1.0"
PLUGIN_FOLDER="${PLUGIN_NAME}_${PLUGIN_VERSION}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="${SCRIPT_DIR}/package/${PLUGIN_FOLDER}"
ADDON_ROOT="${HOME}/Library/Containers/com.kingsoft.wpsoffice.mac/Data/.kingsoft/wps/jsaddons"
DEST_DIR="${ADDON_ROOT}/${PLUGIN_FOLDER}"
PUBLISH_FILE="${ADDON_ROOT}/publish.xml"
PLUGIN_ENTRY="<jsplugin name=\"${PLUGIN_NAME}\" enable=\"enable_dev\" url=\"file://\" type=\"wps\" version=\"${PLUGIN_VERSION}\"/>"

if [[ ! -d "${SOURCE_DIR}" ]]; then
  echo "安装失败：找不到插件包 ${SOURCE_DIR}" >&2
  exit 1
fi

mkdir -p "${ADDON_ROOT}"

if [[ -f "${PUBLISH_FILE}" ]]; then
  BACKUP_FILE="${PUBLISH_FILE}.bak.$(date +%Y%m%d%H%M%S)"
  cp "${PUBLISH_FILE}" "${BACKUP_FILE}"
  echo "已备份现有配置：${BACKUP_FILE}"
else
  cat > "${PUBLISH_FILE}" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<jsplugins>
</jsplugins>
XML
fi

# 移除本插件旧版本配置；保留其他加载项。
perl -0pi -e 's/\s*<jsplugin(?:online)?\b[^>]*\bname="WPS_MAC_READER"[^>]*\/>//g' "${PUBLISH_FILE}"

TMP_FILE="${PUBLISH_FILE}.tmp.$$"
if ! awk -v entry="  ${PLUGIN_ENTRY}" '
  /<\/jsplugins>/ && !inserted { print entry; inserted = 1 }
  { print }
  END { if (!inserted) exit 42 }
' "${PUBLISH_FILE}" > "${TMP_FILE}"; then
  rm -f "${TMP_FILE}"
  echo "安装失败：${PUBLISH_FILE} 缺少 </jsplugins>，请检查 XML 格式。" >&2
  exit 1
fi
mv "${TMP_FILE}" "${PUBLISH_FILE}"

rm -rf "${DEST_DIR}"
mkdir -p "${DEST_DIR}"
cp -R "${SOURCE_DIR}/." "${DEST_DIR}/"
chmod -R u+rwX "${DEST_DIR}"

echo
echo "WPS Mac 纯阅读加载项已安装。"
echo "插件目录：${DEST_DIR}"
echo "配置文件：${PUBLISH_FILE}"
echo
echo "请完全退出并重新打开 WPS 文字，然后查看功能区中的“纯阅读”选项卡。"
