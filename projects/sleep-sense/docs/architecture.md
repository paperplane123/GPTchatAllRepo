# SleepSense v0.1 Architecture

## Goal

Detect a phone posture consistent with a user lying down and holding the device above or near the face, using only public Android APIs.

## Important limitation

A phone sensor cannot directly know the user's body posture. v0.1 therefore detects a proxy condition:

1. the display plane is close to horizontal;
2. the device remains stable;
3. the condition persists for a configured duration.

This proxy is useful for automation experiments but must not be described as definitive human posture recognition.

## Data flow

```text
TYPE_GRAVITY ─────┐
                  ├─> PostureSensorController
TYPE_ACCELEROMETER┘        │
                           ├─> OrientationEstimator
TYPE_GYROSCOPE ────────────┘        │
                                    v
                              LieDownDetector
                                    │
                        UPRIGHT / CANDIDATE /
                           LYING_STABLE
                                    │
                                    v
                           AutomationDispatcher
                                    │
                    Android custom broadcast / UI
```

## Metrics

### Flatness

Let the normalized gravity vector in Android device coordinates be:

```text
g = [gx, gy, gz]
```

The screen normal is the device Z axis. The flatness score is:

```text
flatness = |gz| / ||g||
```

- `flatness ≈ 1`: display plane is close to horizontal.
- `flatness ≈ 0`: display plane is close to vertical.

### Stability

The gyroscope magnitude is:

```text
omega = sqrt(wx² + wy² + wz²)
```

The device is treated as stable when `omega` stays below a configured threshold.

## State machine

```text
UPRIGHT
  │ flatness >= threshold
  v
CANDIDATE
  │ stable for holdDurationMs
  v
LYING_STABLE
  │ flatness drops below threshold
  v
UPRIGHT
```

Movement while flat keeps the detector in `CANDIDATE` and restarts the hold timer.

## Automation boundary

`AutomationDispatcher` deliberately does not change brightness, Do Not Disturb, media playback, or system settings in v0.1. Those operations require separate permissions and user-visible consent. The dispatcher emits a custom broadcast so external automation tools can react without coupling the detector to one vendor.

## Planned v0.2

- Screen-on and foreground-usage context.
- Time-window and ambient-light features.
- Hysteresis and rolling variance rather than a single gyroscope threshold.
- Foreground service with configurable sampling intervals.
- Calibration screen for different holding habits.

## Planned v0.3

- CameraX image stream.
- On-device MediaPipe face landmarks.
- Head roll/pitch estimation.
- Fusion of device orientation, head orientation and interaction context.
