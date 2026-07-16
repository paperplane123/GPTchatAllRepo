package com.paperplane.sleepsense.sensor

import org.junit.Assert.assertEquals
import org.junit.Test

class LieDownDetectorTest {
    @Test
    fun uprightPostureResetsDetector() {
        val detector = LieDownDetector(holdDurationMs = 1_000L)

        detector.update(
            flatness = 0.9f,
            gyroMagnitudeRadPerSec = 0.01f,
            timestampMs = 0L,
        )
        val result = detector.update(
            flatness = 0.2f,
            gyroMagnitudeRadPerSec = 0.01f,
            timestampMs = 2_000L,
        )

        assertEquals(LieDownState.UPRIGHT, result.state)
        assertEquals(0L, result.stableDurationMs)
    }

    @Test
    fun stableFlatPostureBecomesLyingStable() {
        val detector = LieDownDetector(holdDurationMs = 1_000L)

        val candidate = detector.update(
            flatness = 0.9f,
            gyroMagnitudeRadPerSec = 0.01f,
            timestampMs = 10_000L,
        )
        val stable = detector.update(
            flatness = 0.9f,
            gyroMagnitudeRadPerSec = 0.01f,
            timestampMs = 11_100L,
        )

        assertEquals(LieDownState.CANDIDATE, candidate.state)
        assertEquals(LieDownState.LYING_STABLE, stable.state)
    }

    @Test
    fun movementRestartsHoldTimer() {
        val detector = LieDownDetector(holdDurationMs = 1_000L)

        detector.update(
            flatness = 0.9f,
            gyroMagnitudeRadPerSec = 0.01f,
            timestampMs = 0L,
        )
        detector.update(
            flatness = 0.9f,
            gyroMagnitudeRadPerSec = 0.8f,
            timestampMs = 900L,
        )
        val result = detector.update(
            flatness = 0.9f,
            gyroMagnitudeRadPerSec = 0.01f,
            timestampMs = 1_500L,
        )

        assertEquals(LieDownState.CANDIDATE, result.state)
        assertEquals(600L, result.stableDurationMs)
    }
}
