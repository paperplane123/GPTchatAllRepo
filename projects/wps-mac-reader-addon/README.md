# WPS Mac 严格只读阅读加载项

> 状态：实验性 V0.2.0。已针对“选项卡存在但按钮无响应”的 Mac 兼容问题重构回调，并新增不依赖 JavaScript 的 WPS 原生命令备用入口。仍需在具体 WPS Mac 构建上完成真机验证。

这个加载项的目标不是另做一个抽取正文的阅读器，而是让**当前 WPS 文字文档进入不可编辑的阅读版式**：保留原文档页面、图片、表格、公式和排版，只改变当前窗口的查看状态。

## 行为边界

进入严格只读阅读后：

- 使用 WPS 自身的阅读版式显示当前文档；
- 设置 `ReadingLayoutAllowEditing = false`，禁止在阅读版式里修改正文；
- 不添加文档保护，不设置密码；
- 不保存文档，不修改正文和格式；
- 退出阅读后恢复普通页面视图，原文档继续可编辑。

这属于**窗口级临时只读状态**，不是永久加密或文档权限控制。

## 功能区

### 严格只读

- **进入只读阅读**：切换到阅读版式，并显式禁止编辑；
- **重新锁定编辑**：若某个 WPS 构建在阅读过程中重新开放编辑，可再次应用禁止编辑属性；
- **退出只读阅读**：恢复普通页面视图。

### 原生命令备用

直接嵌入 WPS 内置的：

- `ViewFullScreenReadingView`；
- `ViewPrintLayoutView`。

这两个按钮不经过加载项 JavaScript。即使 Mac 构建无法执行自定义回调，原生命令仍有机会正常工作。

## V0.2.0 修复

V0.1.0 在部分 Mac 构建中可能出现选项卡正常显示、所有自定义按钮却没有响应。V0.2.0 修复了两处高风险兼容问题：

1. 同时兼容 `Application`、`wps.Application` 和 `wps` 三种根对象暴露方式；
2. 删除 `main.js` 对标准浏览器 `window` 对象的强依赖，避免隐藏加载页初始化失败。

同时移除了原来的“纯文本任务窗格阅读器”。它不符合“在原文档上只读阅读”的目标。

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
    └── WPS_MAC_READER_0.2.0/
        ├── main.js
        └── ribbon.xml
```

WPS 加载项启动时会自动生成 `index.html` 并加载 `main.js`，因此包内不放 `index.html`。

## 升级或安装

先按 `Command + Q` 完全退出 WPS，再在终端执行：

```bash
( TMP_DIR="$(mktemp -d)"; trap 'rm -rf "$TMP_DIR"' EXIT; git clone --depth 1 --filter=blob:none --sparse https://github.com/paperplane123/GPTchatAllRepo.git "$TMP_DIR/repo" && git -C "$TMP_DIR/repo" sparse-checkout set projects/wps-mac-reader-addon && bash "$TMP_DIR/repo/projects/wps-mac-reader-addon/install.sh" )
```

安装脚本会：

- 备份现有 `publish.xml`；
- 删除本插件的旧注册记录；
- 删除 `WPS_MAC_READER_0.1.0` 等旧版本目录，防止 WPS 读取旧脚本缓存；
- 安装 V0.2.0；
- 保留其他加载项配置和目录。

安装位置：

```text
~/Library/Containers/com.kingsoft.wpsoffice.mac/Data/.kingsoft/wps/jsaddons/
```

重新打开 WPS 文字后，使用：

```text
纯阅读 → 进入只读阅读
```

如果这个按钮仍无响应，先测试右侧：

```text
原生命令备用 → 阅读版式
```

## 卸载

完全退出 WPS 后，在项目目录执行：

```bash
./uninstall.sh
```

脚本会从 `publish.xml` 移除注册记录，并删除本插件的所有历史版本目录。

## 静态校验

需要 Node.js 18 或更高版本：

```bash
npm test
```

校验内容包括：

- V0.2.0 必需文件和 manifest；
- JavaScript 与 Shell 语法；
- 严格只读回调是否存在；
- 是否显式设置 `ReadingLayoutAllowEditing = false`；
- 是否兼容 `wps.Application`；
- 是否错误依赖 `window`；
- 是否提供不依赖 JavaScript 的原生命令入口；
- 安装时是否清理旧版本缓存目录。

## 已知边界

- `ReadingLayoutAllowEditing` 是 WPS 官方公开的阅读版式属性，但不同 Mac 构建的实现完整度仍需真机验证。
- 如果某个构建连 WPS 自身的 `ViewFullScreenReadingView` 都没有实现，则加载项无法凭空补出原生阅读版式。
- 本加载项不会使用 `Document.Protect` 强行保护文档，因为那可能改变文档安全状态并被自动保存；这里只做可随时退出的窗口级只读阅读。

## 设计依据

- WPS `View` 对象公开 `ReadingLayoutAllowEditing`、`ReadingLayout`、`Type` 等阅读版式接口；
- WPS 文字的官方 idMso 列表包含 `ViewFullScreenReadingView` 和 `ViewPrintLayoutView`；
- WPS 加载项通过 `ribbon.xml` 和自动加载的 `main.js` 提供自定义功能区逻辑。
