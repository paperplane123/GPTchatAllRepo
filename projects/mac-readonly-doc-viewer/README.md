# macOS 文档只读阅读器

> 状态：V0.1.0。用于替代在部分 WPS for Mac 构建中“加载项选项卡可见、按钮点击不执行”的失效方案。

这是一个独立的 macOS 小应用，不再依赖 WPS 加载项接口。它调用系统 Quick Look 打开文档预览窗口，界面没有正文编辑、删除、粘贴和保存入口，适合防止阅读时误改 Word 文档。

## 能做什么

- 双击 App 后选择文档；
- 将文档拖到 App 图标上；
- 在 Finder 的“打开方式”中选择该 App；
- 查看、滚动、翻页和缩放；
- 原文件不会被打开为编辑会话。

支持注册的扩展名：

```text
doc docx rtf rtfd odt wps pdf txt
```

其中 `.docx`、`.doc`、`.rtf`、`.pdf` 是否能完整预览取决于 macOS 当前安装的 Quick Look 生成器；`.wps` 格式的支持尤其依赖系统或第三方生成器。

## 与 WPS 阅读模式的区别

- 优点：真正没有编辑入口，不会因光标误触修改正文；不依赖 WPS JS 加载项事件。
- 限制：使用 macOS 预览渲染，不是 WPS 排版内核，复杂字体、域、公式、嵌入对象或分页可能与 WPS 略有差异。

## 安装

终端执行：

```bash
( TMP_DIR="$(mktemp -d)"; trap 'rm -rf "$TMP_DIR"' EXIT; git clone --depth 1 --filter=blob:none --sparse https://github.com/paperplane123/GPTchatAllRepo.git "$TMP_DIR/repo" && git -C "$TMP_DIR/repo" sparse-checkout set projects/mac-readonly-doc-viewer && bash "$TMP_DIR/repo/projects/mac-readonly-doc-viewer/install.sh" )
```

安装位置：

```text
~/Applications/文档只读阅读.app
```

首次运行若 macOS 弹出安全提示，可在 Finder 中右键 App，选择“打开”。

## 使用

### 双击选择文件

打开：

```text
~/Applications/文档只读阅读.app
```

然后选择一个或多个文档。

### 拖放

把 Word 或 PDF 文件拖到 App 图标上。

### Finder 打开方式

右键文件：

```text
打开方式 → 文档只读阅读
```

## 卸载

在项目目录执行：

```bash
bash uninstall.sh
```

或者直接删除：

```text
~/Applications/文档只读阅读.app
```

## 静态校验

```bash
bash test.sh
```

校验安装/卸载脚本语法、Quick Look 调用、Viewer 文件角色和高风险命令。
