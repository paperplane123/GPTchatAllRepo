(function () {
  "use strict";

  var MAX_PARAGRAPHS = 5000;
  var READ_CHUNK_SIZE = 60;
  var SETTINGS_KEY = "wps-mac-reader-settings-v1";
  var NATIVE_READING_COMMAND = "ViewFullScreenReadingView";
  var PANE_STORAGE_KEY = "wpsMacReaderPaneId";

  var elements = {
    documentName: document.getElementById("documentName"),
    status: document.getElementById("statusMessage"),
    content: document.getElementById("readerContent"),
    tocPanel: document.getElementById("tocPanel"),
    tocList: document.getElementById("tocList"),
    toggleTocButton: document.getElementById("toggleTocButton"),
    closeTocButton: document.getElementById("closeTocButton"),
    decreaseFontButton: document.getElementById("decreaseFontButton"),
    increaseFontButton: document.getElementById("increaseFontButton"),
    lineHeightInput: document.getElementById("lineHeightInput"),
    contentWidthInput: document.getElementById("contentWidthInput"),
    nativeReaderButton: document.getElementById("nativeReaderButton"),
    refreshButton: document.getElementById("refreshButton"),
    closeButton: document.getElementById("closeButton")
  };

  var settings = {
    theme: "sepia",
    fontSize: 19,
    lineHeight: 1.8,
    contentWidth: 720
  };

  function clamp(value, minimum, maximum) {
    return Math.min(maximum, Math.max(minimum, value));
  }

  function nextTurn() {
    return new Promise(function (resolve) {
      window.setTimeout(resolve, 0);
    });
  }

  function safeRead(read, fallback) {
    try {
      var value = read();
      return value === undefined || value === null ? fallback : value;
    } catch (error) {
      return fallback;
    }
  }

  function candidateWindows() {
    var candidates = [window];
    try {
      if (window.parent && window.parent !== window) {
        candidates.push(window.parent);
      }
    } catch (error) {
      // Ignore inaccessible frame.
    }
    try {
      if (window.top && candidates.indexOf(window.top) < 0) {
        candidates.push(window.top);
      }
    } catch (error) {
      // Ignore inaccessible frame.
    }
    try {
      if (window.opener && candidates.indexOf(window.opener) < 0) {
        candidates.push(window.opener);
      }
    } catch (error) {
      // Ignore inaccessible opener.
    }
    return candidates;
  }

  function resolveWpsApplication() {
    var contexts = candidateWindows();
    for (var i = 0; i < contexts.length; i += 1) {
      var context = contexts[i];
      var app = safeRead(function () { return context.Application; }, null);
      if (!app) {
        app = safeRead(function () { return context.wps; }, null);
      }
      if (app) {
        return app;
      }
    }
    throw new Error("任务窗格无法访问 WPS Application 对象。");
  }

  function callHostFunction(functionName) {
    var contexts = candidateWindows();
    for (var i = 0; i < contexts.length; i += 1) {
      var context = contexts[i];
      var fn = safeRead(function () { return context[functionName]; }, null);
      if (typeof fn === "function") {
        return fn.call(context);
      }
    }
    return undefined;
  }

  function resolveStoredTaskPane(app) {
    if (!app.PluginStorage || typeof app.PluginStorage.getItem !== "function" || typeof app.GetTaskPane !== "function") {
      return null;
    }

    var paneId = app.PluginStorage.getItem(PANE_STORAGE_KEY);
    if (paneId === undefined || paneId === null || paneId === "") {
      return null;
    }

    try {
      return app.GetTaskPane(Number(paneId));
    } catch (numberError) {
      return app.GetTaskPane(paneId);
    }
  }

  function closeReaderPane() {
    try {
      var app = resolveWpsApplication();
      var pane = resolveStoredTaskPane(app);
      if (pane) {
        pane.Visible = false;
        return true;
      }
    } catch (error) {
      // Fall back to the host callback or embedded window close.
    }

    var result = callHostFunction("CloseReaderPane");
    if (result === undefined) {
      window.close();
    }
    return result !== false;
  }

  function enterNativeReadingMode() {
    try {
      var app = resolveWpsApplication();
      if (!app.ActiveDocument) {
        throw new Error("请先打开一个 WPS 文字文档。");
      }
      if (!app.CommandBars || typeof app.CommandBars.ExecuteMso !== "function") {
        throw new Error("当前 WPS 构建没有暴露原生阅读命令接口。");
      }
      if (typeof app.CommandBars.GetEnabledMso === "function" && app.CommandBars.GetEnabledMso(NATIVE_READING_COMMAND) === false) {
        throw new Error("当前 WPS 构建禁用了原生阅读版式命令。");
      }

      app.CommandBars.ExecuteMso(NATIVE_READING_COMMAND);
      try {
        var view = app.ActiveDocument.ActiveWindow.View;
        view.ReadingLayoutAllowEditing = false;
        view.ReadingLayoutAllowMultiplePages = false;
        view.ReadingLayoutActualView = false;
      } catch (viewError) {
        // The command can still work without exposing every view property.
      }
      closeReaderPane();
      return true;
    } catch (error) {
      var hostResult = callHostFunction("EnterNativeReadingMode");
      if (hostResult === undefined || hostResult === false) {
        setStatus("原生阅读不可用：" + (error && error.message ? error.message : String(error)), true);
        return false;
      }
      return true;
    }
  }

  function cleanParagraphText(value) {
    return String(value || "")
      .replace(/\u0007/g, "")
      .replace(/\u000b/g, "\n")
      .replace(/\f/g, "")
      .replace(/\r/g, "")
      .replace(/\t/g, "    ")
      .replace(/[ \u00a0]+$/g, "");
  }

  function getStyleName(paragraph) {
    var style = safeRead(function () { return paragraph.Style; }, null);
    if (!style) {
      style = safeRead(function () { return paragraph.Range.Style; }, null);
    }
    if (typeof style === "string") {
      return style;
    }
    return String(
      safeRead(function () { return style.NameLocal; }, "") ||
      safeRead(function () { return style.Name; }, "") ||
      ""
    );
  }

  function getHeadingLevel(paragraph) {
    var outlineLevel = Number(safeRead(function () { return paragraph.OutlineLevel; }, NaN));
    if (outlineLevel >= 1 && outlineLevel <= 9) {
      return Math.min(outlineLevel, 6);
    }

    var styleName = getStyleName(paragraph);
    var match = styleName.match(/(?:标题|heading)\s*([1-9])/i);
    if (match) {
      return Math.min(Number(match[1]), 6);
    }
    return null;
  }

  function appendTextWithBreaks(node, text) {
    var lines = String(text).split("\n");
    for (var i = 0; i < lines.length; i += 1) {
      if (i > 0) {
        node.appendChild(document.createElement("br"));
      }
      node.appendChild(document.createTextNode(lines[i]));
    }
  }

  function makeContentNode(text, headingLevel, index) {
    var node;
    if (headingLevel) {
      node = document.createElement("h" + headingLevel);
      node.id = "wps-reader-heading-" + index;
    } else {
      node = document.createElement("p");
    }
    appendTextWithBreaks(node, text);
    return node;
  }

  function makeTocLink(text, headingLevel, index) {
    var link = document.createElement("a");
    link.href = "#wps-reader-heading-" + index;
    link.dataset.level = String(headingLevel);
    link.textContent = text;
    link.addEventListener("click", function () {
      setTocOpen(false);
    });
    return link;
  }

  function setStatus(message, isError) {
    elements.status.textContent = message;
    elements.status.classList.toggle("is-error", Boolean(isError));
  }

  function setTocOpen(open) {
    elements.tocPanel.classList.toggle("is-open", Boolean(open));
  }

  function updateThemeButtons() {
    var buttons = document.querySelectorAll("[data-theme-value]");
    for (var i = 0; i < buttons.length; i += 1) {
      buttons[i].classList.toggle("is-active", buttons[i].dataset.themeValue === settings.theme);
    }
  }

  function applySettings() {
    document.body.dataset.theme = settings.theme;
    document.documentElement.style.setProperty("--reader-font-size", settings.fontSize + "px");
    document.documentElement.style.setProperty("--reader-line-height", String(settings.lineHeight));
    document.documentElement.style.setProperty("--reader-content-width", settings.contentWidth + "px");
    elements.lineHeightInput.value = String(settings.lineHeight);
    elements.contentWidthInput.value = String(settings.contentWidth);
    updateThemeButtons();
  }

  function saveSettings() {
    try {
      window.localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    } catch (error) {
      // Local storage is optional in the embedded browser.
    }
  }

  function loadSettings() {
    try {
      var stored = JSON.parse(window.localStorage.getItem(SETTINGS_KEY) || "null");
      if (stored && typeof stored === "object") {
        if (["light", "sepia", "dark"].indexOf(stored.theme) >= 0) {
          settings.theme = stored.theme;
        }
        settings.fontSize = clamp(Number(stored.fontSize) || settings.fontSize, 14, 32);
        settings.lineHeight = clamp(Number(stored.lineHeight) || settings.lineHeight, 1.4, 2.4);
        settings.contentWidth = clamp(Number(stored.contentWidth) || settings.contentWidth, 520, 1000);
      }
    } catch (error) {
      // Ignore invalid or unavailable stored settings.
    }
    applySettings();
  }

  async function loadActiveDocument() {
    elements.content.replaceChildren();
    elements.tocList.replaceChildren();
    setStatus("正在连接 WPS 文档接口…", false);
    elements.documentName.textContent = "正在读取文档…";

    try {
      var app = resolveWpsApplication();
      var activeDocument = safeRead(function () { return app.ActiveDocument; }, null);
      if (!activeDocument) {
        throw new Error("没有打开的 WPS 文字文档。");
      }

      var documentName = String(safeRead(function () { return activeDocument.Name; }, "当前文档"));
      elements.documentName.textContent = documentName;

      var paragraphs = safeRead(function () { return activeDocument.Paragraphs; }, null);
      if (!paragraphs) {
        throw new Error("当前 WPS 构建没有暴露 ActiveDocument.Paragraphs。");
      }

      var paragraphCount = Number(safeRead(function () { return paragraphs.Count; }, 0));
      if (!Number.isFinite(paragraphCount) || paragraphCount < 1) {
        throw new Error("当前文档没有可读取的正文段落。");
      }

      var readLimit = Math.min(paragraphCount, MAX_PARAGRAPHS);
      var contentFragment = document.createDocumentFragment();
      var tocFragment = document.createDocumentFragment();
      var renderedCount = 0;
      var headingCount = 0;
      var failedCount = 0;
      var consecutiveEmpty = 0;

      for (var index = 1; index <= readLimit; index += 1) {
        try {
          var paragraph = paragraphs.Item(index);
          var rawText = safeRead(function () { return paragraph.Range.Text; }, "");
          var text = cleanParagraphText(rawText);

          if (!text.trim()) {
            consecutiveEmpty += 1;
            if (consecutiveEmpty <= 2) {
              var spacer = document.createElement("p");
              spacer.className = "reader-empty";
              spacer.setAttribute("aria-hidden", "true");
              spacer.innerHTML = "&nbsp;";
              contentFragment.appendChild(spacer);
            }
          } else {
            consecutiveEmpty = 0;
            var headingLevel = getHeadingLevel(paragraph);
            contentFragment.appendChild(makeContentNode(text, headingLevel, index));
            renderedCount += 1;

            if (headingLevel) {
              tocFragment.appendChild(makeTocLink(text, headingLevel, index));
              headingCount += 1;
            }
          }
        } catch (paragraphError) {
          failedCount += 1;
        }

        if (index % READ_CHUNK_SIZE === 0) {
          elements.content.appendChild(contentFragment);
          contentFragment = document.createDocumentFragment();
          setStatus("正在读取：" + index + " / " + readLimit + " 段…", false);
          await nextTurn();
        }
      }

      elements.content.appendChild(contentFragment);
      elements.tocList.appendChild(tocFragment);

      if (renderedCount === 0) {
        throw new Error("读取到了段落对象，但没有获得可显示的文本。文档可能只包含图片、文本框或受保护内容。");
      }

      if (headingCount === 0) {
        var emptyToc = document.createElement("div");
        emptyToc.className = "toc-empty";
        emptyToc.textContent = "没有检测到标题样式或大纲级别。";
        elements.tocList.appendChild(emptyToc);
      }

      var summary = "已读取 " + renderedCount + " 个正文段落";
      if (headingCount > 0) {
        summary += "，识别 " + headingCount + " 个标题";
      }
      if (failedCount > 0) {
        summary += "，跳过 " + failedCount + " 个无法访问的段落";
      }
      if (paragraphCount > readLimit) {
        summary += "；文档共 " + paragraphCount + " 段，当前为防卡顿只读取前 " + readLimit + " 段";
      }
      setStatus(summary + "。", false);
    } catch (error) {
      var message = error && error.message ? error.message : String(error);
      setStatus("读取失败：" + message, true);
      elements.documentName.textContent = "无法读取当前文档";

      var explanation = document.createElement("p");
      explanation.textContent = "请确认当前窗口是 WPS 文字文档，并尝试从功能区重新打开阅读器。加载项不会修改原文档。";
      elements.content.appendChild(explanation);
    }
  }

  function changeFontSize(delta) {
    settings.fontSize = clamp(settings.fontSize + delta, 14, 32);
    applySettings();
    saveSettings();
  }

  function bindControls() {
    elements.toggleTocButton.addEventListener("click", function () {
      setTocOpen(!elements.tocPanel.classList.contains("is-open"));
    });
    elements.closeTocButton.addEventListener("click", function () {
      setTocOpen(false);
    });
    elements.decreaseFontButton.addEventListener("click", function () {
      changeFontSize(-1);
    });
    elements.increaseFontButton.addEventListener("click", function () {
      changeFontSize(1);
    });
    elements.lineHeightInput.addEventListener("input", function () {
      settings.lineHeight = clamp(Number(elements.lineHeightInput.value), 1.4, 2.4);
      applySettings();
      saveSettings();
    });
    elements.contentWidthInput.addEventListener("input", function () {
      settings.contentWidth = clamp(Number(elements.contentWidthInput.value), 520, 1000);
      applySettings();
      saveSettings();
    });
    elements.refreshButton.addEventListener("click", loadActiveDocument);
    elements.nativeReaderButton.addEventListener("click", enterNativeReadingMode);
    elements.closeButton.addEventListener("click", closeReaderPane);

    var themeButtons = document.querySelectorAll("[data-theme-value]");
    for (var i = 0; i < themeButtons.length; i += 1) {
      themeButtons[i].addEventListener("click", function (event) {
        settings.theme = event.currentTarget.dataset.themeValue;
        applySettings();
        saveSettings();
      });
    }

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        if (elements.tocPanel.classList.contains("is-open")) {
          setTocOpen(false);
        } else {
          closeReaderPane();
        }
      }
      if ((event.metaKey || event.ctrlKey) && (event.key === "+" || event.key === "=")) {
        event.preventDefault();
        changeFontSize(1);
      }
      if ((event.metaKey || event.ctrlKey) && event.key === "-") {
        event.preventDefault();
        changeFontSize(-1);
      }
    });
  }

  loadSettings();
  bindControls();
  loadActiveDocument();
}());
