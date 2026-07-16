package com.paperplane.sleepsense.sensor

enum class LieDownState {
    UPRIGHT,
    CANDIDATE,
    LYING_STABLE,
}

data class DetectorResult(
    val state: LieDownState,
    val stableDurationMs: Long,
    val isFlatEnough: Boolean,
    val isStillEnough: Boolean,
)

class LieDownDetector(
    private val flatnessThreshold: Float = 0.72f,
    private val stillnessThresholdRadPerSec: Float = 0.18f,
    private val holdDurationMs: Long = 8_000L,
) {
    private var candidateSinceMs: Long? = null

    var state: LieDownState = LieDownState.UPRIGHT
        private set

    fun update(
        flatness: Float,
        gyroMagnitudeRadPerSec: Float,
        timestampMs: Long,
    ): DetectorResult {
        val isFlatEnough = flatness >= flatnessThreshold
        val isStillEnough = gyroMagnitudeRadPerSec <= stillnessThresholdRadPerSec

        if (!isFlatEnough) {
            candidateSinceMs = null
            state = LieDownState.UPRIGHT
            return DetectorResult(
                state = state,
                stableDurationMs = 0L,
                isFlatEnough = false,
                isStillEnough = isStillEnough,
            )
        }

        if (!isStillEnough) {
            candidateSinceMs = timestampMs
            state = LieDownState.CANDIDATE
            return DetectorResult(
                state = state,
                stableDurationMs = 0L,
                isFlatEnough = true,
                isStillEnough = false,
            )
        }

        val startedAt = candidateSinceMs ?: timestampMs.also { candidateSinceMs = it }
        val stableDurationMs = (timestampMs - startedAt).coerceAtLeast(0L)
        state = if (stableDurationMs >= holdDurationMs) {
            LieDownState.LYING_STABLE
        } else {
            LieDownState.CANDIDATE
        }

        return DetectorResult(
            state = state,
            stableDurationMs = stableDurationMs,
            isFlatEnough = true,
            isStillEnough = true,
        )
    }

    fun reset() {
        candidateSinceMs = null
        state = LieDownState.UPRIGHT
    }
}
