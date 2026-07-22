/* global Application, wps, alert */

var WD_PRINT_VIEW = 3;
var WD_READING_VIEW = 7;
var READING_COMMAND = "ViewFullScreenReadingView";
var PRINT_COMMAND = "ViewPrintLayoutView";

function getReaderApplication() {
  if (typeof Application !== "undefined" && Application) {
    return Application;
  }

  if (typeof wps !== "undefined" && wps) {
    if (wps.Application) {
      return wps.Application;
    }
    return wps;
  }

  throw new Error("无法取得 WPS Application 对象。");
}

function showReaderError(message) {
  try {
    var app = getReaderApplication();
    if (typeof app.alert === "function") {
      app.alert(message);
      return;
    }
  } catch (ignored) {
    // Fall through to the JavaScript alert when available.
  }

  if (typeof alert === "function") {
    alert(message);
  }
}

function getActiveReaderView(app) {
  if (!app.ActiveDocument) {
    throw new Error("请先打开一个 WPS 文字文档。");
  }
  if (!app.ActiveDocument.ActiveWindow) {
    throw new Error("当前文档没有活动窗口。");
  }
  return app.ActiveDocument.ActiveWindow.View;
}

function setReadOnlyReadingProperties(view) {
  var applied = false;

  try {
    view.ReadingLayoutAllowEditing = false;
    applied = true;
  } catch (ignoredAllowEditing) {
    // Older Mac builds may omit this property.
  }

  try {
    view.ReadingLayoutAllowMultiplePages = false;
  } catch (ignoredMultiplePages) {
    // Optional compatibility setting.
  }

  try {
    view.ReadingLayoutActualView = true;
  } catch (ignoredActualView) {
    // Optional compatibility setting.
  }

  return applied;
}

function enterReadingLayout(app, view) {
  var entered = false;

  // Preferred path: switch the View object directly.
  try {
    view.ReadingLayout = true;
    entered = true;
  } catch (ignoredReadingLayout) {
    // Fall through to Type or the built-in command.
  }

  if (!entered) {
    try {
      view.Type = WD_READING_VIEW;
      entered = true;
    } catch (ignoredViewType) {
      // Fall through to the built-in command.
    }
  }

  if (!entered && app.CommandBars && typeof app.CommandBars.ExecuteMso === "function") {
    app.CommandBars.ExecuteMso(READING_COMMAND);
    entered = true;
  }

  return entered;
}

function EnterStrictReadOnlyMode(control) {
  try {
    var app = getReaderApplication();
    var view = getActiveReaderView(app);

    // Apply before and after switching because some builds recreate the View object.
    setReadOnlyReadingProperties(view);

    if (!enterReadingLayout(app, view)) {
      throw new Error("当前 WPS Mac 构建没有可用的阅读版式接口。");
    }

    view = getActiveReaderView(app);
    setReadOnlyReadingProperties(view);

    try {
      app.StatusBar = "已进入只读阅读模式：正文编辑已禁用";
    } catch (ignoredStatusBar) {
      // StatusBar is optional.
    }

    return true;
  } catch (error) {
    showReaderError("进入只读阅读模式失败：" + (error && error.message ? error.message : String(error)));
    return false;
  }
}

function ExitStrictReadOnlyMode(control) {
  try {
    var app = getReaderApplication();
    var view = getActiveReaderView(app);
    var exited = false;

    try {
      view.ReadingLayout = false;
      exited = true;
    } catch (ignoredReadingLayout) {
      // Fall through.
    }

    if (!exited) {
      try {
        view.Type = WD_PRINT_VIEW;
        exited = true;
      } catch (ignoredViewType) {
        // Fall through.
      }
    }

    if (!exited && app.CommandBars && typeof app.CommandBars.ExecuteMso === "function") {
      app.CommandBars.ExecuteMso(PRINT_COMMAND);
      exited = true;
    }

    if (!exited) {
      throw new Error("当前 WPS Mac 构建无法恢复页面视图。");
    }

    try {
      app.StatusBar = "已退出只读阅读模式";
    } catch (ignoredStatusBar) {
      // StatusBar is optional.
    }

    return true;
  } catch (error) {
    showReaderError("退出只读阅读模式失败：" + (error && error.message ? error.message : String(error)));
    return false;
  }
}

function ReapplyReadOnlyLock(control) {
  try {
    var app = getReaderApplication();
    var view = getActiveReaderView(app);
    setReadOnlyReadingProperties(view);
    return true;
  } catch (error) {
    showReaderError("重新锁定编辑失败：" + (error && error.message ? error.message : String(error)));
    return false;
  }
}
