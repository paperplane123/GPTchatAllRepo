# WPS Mac 纯阅读加载项

> 状态：实验性 V0.1.0。代码和安装结构已完成静态校验，但尚未在用户的具体 WPS Mac 构建上完成真机验证；尤其是隐藏命令 `ViewFullScreenReadingView` 是否生效，取决于该构建是否保留对应实现。

这是一个面向 **WPS 文字 Mac 版** 的轻量加载项，解决没有明显“纯阅读模式”入口的问题。

## 功能

- **原生阅读**：尝试调用 WPS 内置隐藏命令 `ViewFullScreenReadingView`。
- **纯阅读器兜底**：原生命令不工作时，在 WPS 侧边任务窗格中读取当前文档正文。
- 阅读器支持：
  - 浅色、米黄、深色三种主题；
  - 字号、行距、正文宽度调节；
  - 按标题/大纲级别生成目录；
  - 一键重新读取当前文档；
  - `Esc` 关闭阅读器。
- 加载项只读取文档，不修改正文。

## 目录结构

```text
wps-mac-reader-addon/
├── install.sh
├── uninstall.sh
├── package.json
├── scripts/
│   └── validate.mjs
└── package/
    ├── publish.xml
    └── WPS_MAC_READER_0.1.0/
        ├── main.js
        ├── ribbon.xml
        ├── reader.html
        ├── reader.css
        └── reader.js
```

WPS 加载项启动时会自动生成 `index.html` 并加载 `main.js`，因此包内故意不放 `index.html`。

## 安装

安装前先完全退出 WPS，包括所有 WPS 文字窗口。

### 从 GitHub 一行安装

终端粘贴以下命令。它使用 Git 稀疏克隆，只检出这个插件目录，安装完成后删除临时下载文件：

```bash
TMP_DIR="$(mktemp -d)" && git clone --depth 1 --filter=blob:none --sparse https://github.com/paperplane123/GPTchatAllRepo.git "$TMP_DIR/repo" && git -C "$TMP_DIR/repo" sparse-checkout set projects/wps-mac-reader-addon && bash "$TMP_DIR/repo/projects/wps-mac-reader-addon/install.sh"; STATUS=$?; rm -rf "$TMP_DIR"; exit $STATUS
```

### 已下载仓库时安装

1. 在终端进入本项目目录。
2. 执行：

```bash
chmod +x install.sh uninstall.sh
./install.sh
```

安装后重新打开 WPS 文字，功能区中应出现 **“纯阅读”** 选项卡。

安装脚本会：

- 将插件文件复制到：

```text
~/Library/Containers/com.kingsoft.wpsoffice.mac/Data/.kingsoft/wps/jsaddons/
```

- 保留并备份已有 `publish.xml`；
- 删除本插件的旧配置，再写入 V0.1.0 配置；
- 不触碰其他加载项的文件。

## 使用

### 原生阅读

点击 **纯阅读 → 原生阅读**。

加载项会执行：

```javascript
Application.CommandBars.ExecuteMso("ViewFullScreenReadingView")
```

如果当前 WPS Mac 构建没有实现该命令，加载项会自动尝试打开兜底阅读器；若 WPS 静默忽略命令，可直接点击 **打开阅读器**。

### 兜底阅读器

点击 **纯阅读 → 打开阅读器**。

阅读器会逐段读取 `ActiveDocument.Paragraphs`，使用段落 `OutlineLevel` 或标题样式生成目录。表格、文本框、公式和浮动对象目前只做降级文本展示，不追求原版式还原。

## 卸载

完全退出 WPS 后执行：

```bash
./uninstall.sh
```

脚本会删除插件目录，并从 `publish.xml` 中移除本插件配置。

## 静态校验

需要 Node.js 18 或更高版本：

```bash
npm test
```

校验内容包括：

- 必需文件是否存在；
- JavaScript 语法；
- `publish.xml` 的插件名称、类型、版本；
- `ribbon.xml` 的按钮回调是否在 `main.js` 中实现；
- 安装和卸载脚本 Shell 语法。

## 已知边界

- 未在所有 Intel / Apple Silicon 和不同 WPS Mac 版本上验证。
- Mac 版 WPS 目前通常不能依赖 58890 端口完成网页一键安装，因此采用本地离线目录安装。
- WPS 若完全不暴露任务窗格或文档对象接口，兜底阅读器会显示错误说明，不会修改文档。
- 超长文档默认最多读取 5000 个段落，避免任务窗格无响应。
- 当前不渲染图片、批注、脚注、页眉页脚和复杂表格布局。

## 设计依据

- WPS 加载项由 `ribbon.xml` 和网页脚本组成，启动时自动创建 `index.html` 并引入 `main.js`。
- WPS 文字的官方 idMso 列表包含 `ViewFullScreenReadingView`、`ProtectEyes` 等命令。
- WPS Mac 支持加载项能力，但离线部署通常需要手工写入沙盒目录下的 `jsaddons/publish.xml`。
