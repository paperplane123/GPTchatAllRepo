package com.paperplane.sleepsense.sensor

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import kotlin.math.abs
import kotlin.math.acos
import kotlin.math.sqrt

data class PostureReading(
    val flatness: Float = 0f,
    val tiltFromHorizontalDegrees: Float = 90f,
    val gyroMagnitudeRadPerSec: Float = 0f,
    val stableDurationMs: Long = 0L,
    val state: LieDownState = LieDownState.UPRIGHT,
    val usingAccelerometerFallback: Boolean = false,
)

class PostureSensorController(
    context: Context,
    private val onReading: (PostureReading) -> Unit,
    private val onStateChanged: (LieDownState, PostureReading) -> Unit,
) : SensorEventListener {
    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val gravitySensor = sensorManager.getDefaultSensor(Sensor.TYPE_GRAVITY)
    private val accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
    private val gyroscope = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)
    private val detector = LieDownDetector()

    private val filteredAcceleration = FloatArray(3)
    private val gravityVector = FloatArray(3)
    private var gyroMagnitudeRadPerSec = 0f
    private var lastState = LieDownState.UPRIGHT

    private val usingAccelerometerFallback: Boolean
        get() = gravitySensor == null

    fun start() {
        val postureSensor = gravitySensor ?: accelerometer
        postureSensor?.let {
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_UI)
        }
        gyroscope?.let {
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_UI)
        }
    }

    fun stop() {
        sensorManager.unregisterListener(this)
        detector.reset()
        lastState = LieDownState.UPRIGHT
    }

    override fun onSensorChanged(event: SensorEvent) {
        when (event.sensor.type) {
            Sensor.TYPE_GRAVITY -> {
                gravityVector[0] = event.values[0]
                gravityVector[1] = event.values[1]
                gravityVector[2] = event.values[2]
                publish(event.timestamp / 1_000_000L)
            }

            Sensor.TYPE_ACCELEROMETER -> {
                val alpha = 0.82f
                for (index in 0..2) {
                    filteredAcceleration[index] =
                        alpha * filteredAcceleration[index] + (1f - alpha) * event.values[index]
                    gravityVector[index] = filteredAcceleration[index]
                }
                publish(event.timestamp / 1_000_000L)
            }

            Sensor.TYPE_GYROSCOPE -> {
                gyroMagnitudeRadPerSec = magnitude(event.values[0], event.values[1], event.values[2])
            }
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit

    private fun publish(timestampMs: Long) {
        val gravityMagnitude = magnitude(gravityVector[0], gravityVector[1], gravityVector[2])
        if (gravityMagnitude < 0.1f) return

        val flatness = (abs(gravityVector[2]) / gravityMagnitude).coerceIn(0f, 1f)
        val tiltDegrees = Math.toDegrees(acos(flatness.toDouble())).toFloat()
        val result = detector.update(
            flatness = flatness,
            gyroMagnitudeRadPerSec = gyroMagnitudeRadPerSec,
            timestampMs = timestampMs,
        )

        val reading = PostureReading(
            flatness = flatness,
            tiltFromHorizontalDegrees = tiltDegrees,
            gyroMagnitudeRadPerSec = gyroMagnitudeRadPerSec,
            stableDurationMs = result.stableDurationMs,
            state = result.state,
            usingAccelerometerFallback = usingAccelerometerFallback,
        )

        onReading(reading)
        if (result.state != lastState) {
            lastState = result.state
            onStateChanged(result.state, reading)
        }
    }

    private fun magnitude(x: Float, y: Float, z: Float): Float = sqrt(x * x + y * y + z * z)
}
