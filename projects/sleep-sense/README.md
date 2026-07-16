# SleepSense

SleepSense 是一个 Android 本地姿态感知实验项目。第一版不调用小米私有“注视感知”接口，而是使用 Android 公开传感器 API，判断手机是否处于一种与“用户躺着看手机”相符的姿态，并把状态变化暴露给自动化工具。

> 当前状态：MVP 过程稿。它检测的是“手机近似水平、持续静止且屏幕正在使用”的组合状态，不等同于医学意义或系统级的人体躺卧识别。

## v0.1 已实现

- Kotlin + Jetpack Compose 单页 Demo。
- 优先使用重力传感器，缺失时回退到加速度计低通滤波。
- 使用陀螺仪判断手机是否稳定。
- 三态状态机：`UPRIGHT`、`CANDIDATE`、`LYING_STABLE`。
- 实时显示屏幕平面倾角、平放置信度和陀螺仪角速度。
- 状态进入 `LYING_STABLE` 时发送 Android 广播，便于 Tasker、MacroDroid 或后续自研自动化模块接入。

## 自动化广播

Action：

```text
com.paperplane.sleepsense.action.POSTURE_CHANGED
```

Extras：

```text
state: UPRIGHT | CANDIDATE | LYING_STABLE
flatness: 0.0 ~ 1.0
stable_duration_ms: 稳定持续时间
```

## 运行

1. 使用 Android Studio 打开 `projects/sleep-sense/android`。
2. 等待 Gradle Sync 完成。
3. 连接 Android 8.0 及以上设备。
4. 运行 `app`。
5. 将手机从竖直姿态缓慢转为屏幕近似水平，并保持稳定约 8 秒，观察状态变化。

当前仓库未提交 Gradle Wrapper 二进制 JAR，因此推荐直接使用 Android Studio 自带的 Gradle 环境。首次本地打开后可执行 `gradle wrapper` 补齐 Wrapper。

## 下一步

- 增加前台服务与低功耗采样。
- 引入屏幕开关、时间段、环境光等上下文。
- 增加 CameraX + MediaPipe Face Landmarker，联合估计手机姿态与头部姿态。
- 提供 Tasker 插件、Webhook、Intent 和系统设置快捷动作。
