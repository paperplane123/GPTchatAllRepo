#!/bin/bash
set -euo pipefail

APP_NAME="文档只读阅读.app"
APP_VERSION="0.1.0"
BUNDLE_ID="com.paperplane123.readonly-document-viewer"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_SCRIPT="${SCRIPT_DIR}/readonly-viewer.applescript"
INSTALL_DIR="${HOME}/Applications"
APP_PATH="${INSTALL_DIR}/${APP_NAME}"
INFO_PLIST="${APP_PATH}/Contents/Info.plist"
PLIST_BUDDY="/usr/libexec/PlistBuddy"
LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "安装失败：这个查看器只支持 macOS。" >&2
  exit 1
fi

for required in /usr/bin/osacompile /usr/bin/qlmanage "${PLIST_BUDDY}"; do
  if [[ ! -x "${required}" ]]; then
    echo "安装失败：系统缺少 ${required}" >&2
    exit 1
  fi
done

if [[ ! -f "${SOURCE_SCRIPT}" ]]; then
  echo "安装失败：找不到 ${SOURCE_SCRIPT}" >&2
  exit 1
fi

mkdir -p "${INSTALL_DIR}"
rm -rf "${APP_PATH}"
/usr/bin/osacompile -o "${APP_PATH}" "${SOURCE_SCRIPT}"

set_string() {
  local key="$1"
  local value="$2"
  if "${PLIST_BUDDY}" -c "Print :${key}" "${INFO_PLIST}" >/dev/null 2>&1; then
    "${PLIST_BUDDY}" -c "Set :${key} ${value}" "${INFO_PLIST}"
  else
    "${PLIST_BUDDY}" -c "Add :${key} string ${value}" "${INFO_PLIST}"
  fi
}

set_bool() {
  local key="$1"
  local value="$2"
  if "${PLIST_BUDDY}" -c "Print :${key}" "${INFO_PLIST}" >/dev/null 2>&1; then
    "${PLIST_BUDDY}" -c "Set :${key} ${value}" "${INFO_PLIST}"
  else
    "${PLIST_BUDDY}" -c "Add :${key} bool ${value}" "${INFO_PLIST}"
  fi
}

set_string "CFBundleIdentifier" "${BUNDLE_ID}"
set_string "CFBundleName" "文档只读阅读"
set_string "CFBundleDisplayName" "文档只读阅读"
set_string "CFBundleShortVersionString" "${APP_VERSION}"
set_string "CFBundleVersion" "1"
set_bool "NSHighResolutionCapable" "true"

"${PLIST_BUDDY}" -c "Delete :CFBundleDocumentTypes" "${INFO_PLIST}" >/dev/null 2>&1 || true
"${PLIST_BUDDY}" -c "Add :CFBundleDocumentTypes array" "${INFO_PLIST}"
"${PLIST_BUDDY}" -c "Add :CFBundleDocumentTypes:0 dict" "${INFO_PLIST}"
"${PLIST_BUDDY}" -c "Add :CFBundleDocumentTypes:0:CFBundleTypeName string 文档" "${INFO_PLIST}"
"${PLIST_BUDDY}" -c "Add :CFBundleDocumentTypes:0:CFBundleTypeRole string Viewer" "${INFO_PLIST}"
"${PLIST_BUDDY}" -c "Add :CFBundleDocumentTypes:0:LSHandlerRank string Alternate" "${INFO_PLIST}"
"${PLIST_BUDDY}" -c "Add :CFBundleDocumentTypes:0:CFBundleTypeExtensions array" "${INFO_PLIST}"

extensions=(doc docx rtf rtfd odt wps pdf txt)
for index in "${!extensions[@]}"; do
  "${PLIST_BUDDY}" -c "Add :CFBundleDocumentTypes:0:CFBundleTypeExtensions:${index} string ${extensions[$index]}" "${INFO_PLIST}"
done

/usr/bin/touch "${APP_PATH}"
if [[ -x "${LSREGISTER}" ]]; then
  "${LSREGISTER}" -f "${APP_PATH}" >/dev/null 2>&1 || true
fi

cat <<EOF

安装完成：${APP_PATH}

使用方式：
1. 双击“文档只读阅读”，选择 Word/PDF 文档；或
2. 将文档直接拖到 App 图标上；或
3. Finder 右键文档 → 打开方式 → 文档只读阅读。

这是系统预览窗口，没有正文编辑和保存入口。
EOF
