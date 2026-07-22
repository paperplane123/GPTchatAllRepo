/* global Application, wps */

var WPS_READER_NATIVE_COMMAND = "ViewFullScreenReadingView";
var WPS_READER_PRINT_COMMAND = "ViewPrintLayoutView";
var WPS_READER_PANE_WIDTH = 620;
var wpsReaderRibbonUI = null;
var wpsReaderPane = null;

function getWpsApplication() {
  if (typeof Application !== "undefined") {
    return Application;
  }
  if (typeof wps !== "undefined") {
    return wps;
  }
  throw new Error("当前页面无法访问 WPS Application 对象。");
}

function getAddonResourceUrl(fileName) {
  try {
    return new URL(fileName, window.location.href).href;
  } catch (error) {
    var base = String(window.location.href || "").replace(/[^/]*$/, "");
    return base + fileName;
  }
}

function showWpsReaderMessage(message) {
  try {
    var app = getWpsApplication();
    if (typeof app.alert === "function") {
      app.alert(message);
      return;
    }
  } catch (error) {
    // Fall through to the browser alert.
  }
  if (typeof window.alert === "function") {
    window.alert(message);
  }
}

function OnAddInLoad(ribbonUI) {
  wpsReaderRibbonUI = ribbonUI || null;
  return true;
}

function configureNativeReadingView(app) {
  try {
    var view = app.ActiveDocument.ActiveWindow.View;
    view.ReadingLayoutAllowEditing = false;
    view.ReadingLayoutAllowMultiplePages = false;
    view.ReadingLayoutActualView = false;
  } catch (error) {
    // Some Mac builds expose the command but not every reading-layout property.
  }
}

function getNativeReadingPressedState(app) {
  try {
    if (app.CommandBars && typeof app.CommandBars.GetPressedMso === "function") {
      return Boolean(app.CommandBars.GetPressedMso(WPS_READER_NATIVE_COMMAND));
    }
  } catch (error) {
    // Unknown means the current build does not expose a reliable state query.
  }
  return null;
}

function EnterNativeReadingMode() {
  var app;
  try {
    app = getWpsApplication();
    if (!app.ActiveDocument) {
      throw new Error("请先打开一个 WPS 文字文档。");
    }

    var wasPressed = getNativeReadingPressedState(app);
    if (!app.CommandBars || typeof app.CommandBars.ExecuteMso !== "function") {
      throw new Error("当前 WPS 构建没有暴露 CommandBars.ExecuteMso。");
    }

    if (typeof app.CommandBars.GetEnabledMso === "function") {
      var enabled = app.CommandBars.GetEnabledMso(WPS_READER_NATIVE_COMMAND);
      if (enabled === false) {
        throw new Error("当前 WPS 构建禁用了原生阅读版式命令。");
      }
    }

    app.CommandBars.ExecuteMso(WPS_READER_NATIVE_COMMAND);

    // If the command was already active, this click intentionally toggles it off.
    if (wasPressed === true) {
      return true;
    }

    configureNativeReadingView(app);

    // Some Mac builds silently ignore the idMso instead of throwing an error.
    window.setTimeout(function () {
      var pressed = getNativeReadingPressedState(app);
      if (pressed === false) {
        OpenReaderPane();
      } else if (pressed === true) {
        configureNativeReadingView(app);
      }
    }, 700);

    return true;
  } catch (error) {
    OpenReaderPane();
    return false;
  }
}

function OpenReaderPane() {
  try {
    var app = getWpsApplication();
    if (!app.ActiveDocument) {
      throw new Error("请先打开一个 WPS 文字文档。");
    }

    if (wpsReaderPane) {
      try {
        wpsReaderPane.Visible = true;
        return true;
      } catch (error) {
        wpsReaderPane = null;
      }
    }

    var paneUrl = getAddonResourceUrl("reader.html");
    wpsReaderPane = app.CreateTaskPane(paneUrl, "纯阅读");
    if (!wpsReaderPane) {
      throw new Error("WPS 拒绝创建任务窗格，可能是本地 URL 安全检查未通过。");
    }

    try {
      wpsReaderPane.Width = WPS_READER_PANE_WIDTH;
    } catch (error) {
      // Width is optional on some builds.
    }
    wpsReaderPane.Visible = true;
    return true;
  } catch (error) {
    showWpsReaderMessage("无法打开纯阅读器：" + (error && error.message ? error.message : String(error)));
    return false;
  }
}

function CloseReaderPane() {
  if (!wpsReaderPane) {
    return true;
  }
  try {
    wpsReaderPane.Visible = false;
  } catch (error) {
    wpsReaderPane = null;
  }
  return true;
}

function RefreshReaderPane() {
  if (wpsReaderPane) {
    try {
      wpsReaderPane.Visible = false;
    } catch (error) {
      // Recreate below.
    }
    wpsReaderPane = null;
  }
  return OpenReaderPane();
}

function ExitReadingMode() {
  try {
    var app = getWpsApplication();
    if (app.CommandBars && typeof app.CommandBars.ExecuteMso === "function") {
      app.CommandBars.ExecuteMso(WPS_READER_PRINT_COMMAND);
    }
  } catch (error) {
    // Closing the custom reader is still useful even if native view reset fails.
  }
  CloseReaderPane();
  return true;
}

// Explicitly expose callbacks for WPS CustomUI and the task-pane page.
window.OnAddInLoad = OnAddInLoad;
window.EnterNativeReadingMode = EnterNativeReadingMode;
window.OpenReaderPane = OpenReaderPane;
window.CloseReaderPane = CloseReaderPane;
window.RefreshReaderPane = RefreshReaderPane;
window.ExitReadingMode = ExitReadingMode;
