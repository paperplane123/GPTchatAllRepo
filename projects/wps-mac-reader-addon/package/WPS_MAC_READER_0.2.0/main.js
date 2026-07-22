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

function readViewType(view) {
  try {
    var value = Number(view.Type);
    return isNaN(value) ? null : value;
  } catch (ignored) {
    return null;
  }
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
  // WPS officially documents View.Type as writable. Verify the state after assignment
  // instead of assuming that a silent COM-proxy assignment succeeded.
  try {
    view.Type = WD_READING_VIEW;
    if (readViewType(view) === WD_READING_VIEW) {
      return true;
    }
  } catch (ignoredViewType) {
    // Fall through.
  }

  try {
    view.ReadingLayout = true;
    if (view.ReadingLayout === true || readViewType(view) === WD_READING_VIEW) {
      return true;
    }
  } catch (ignoredReadingLayout) {
    // Fall through.
  }

  if (app.CommandBars && typeof app.CommandBars.ExecuteMso === "function") {
    app.CommandBars.ExecuteMso(READING_COMMAND);
    return true;
  }

  return false;
}

function exitReadingLayout(app, view) {
  try {
    view.Type = WD_PRINT_VIEW;
    if (readViewType(view) === WD_PRINT_VIEW) {
      return true;
    }
  } catch (ignoredViewType) {
    // Fall through.
  }

  try {
    view.ReadingLayout = false;
    if (view.ReadingLayout === false || readViewType(view) === WD_PRINT_VIEW) {
      return true;
    }
  } catch (ignoredReadingLayout) {
    // Fall through.
  }

  if (app.CommandBars && typeof app.CommandBars.ExecuteMso === "function") {
    app.CommandBars.ExecuteMso(PRINT_COMMAND);
    return true;
  }

  return false;
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

    if (!exitReadingLayout(app, view)) {
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
    if (!setReadOnlyReadingProperties(view)) {
      throw new Error("当前 WPS Mac 构建没有暴露 ReadingLayoutAllowEditing 属性。");
    }
    return true;
  } catch (error) {
    showReaderError("重新锁定编辑失败：" + (error && error.message ? error.message : String(error)));
    return false;
  }
}
