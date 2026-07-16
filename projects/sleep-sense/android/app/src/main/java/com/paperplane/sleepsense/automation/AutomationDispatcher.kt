package com.paperplane.sleepsense.automation

import android.content.Context
import android.content.Intent
import com.paperplane.sleepsense.sensor.LieDownState
import com.paperplane.sleepsense.sensor.PostureReading

class AutomationDispatcher(
    private val context: Context,
) {
    fun dispatch(state: LieDownState, reading: PostureReading) {
        val intent = Intent(ACTION_POSTURE_CHANGED).apply {
            addFlags(Intent.FLAG_RECEIVER_FOREGROUND)
            putExtra(EXTRA_STATE, state.name)
            putExtra(EXTRA_FLATNESS, reading.flatness)
            putExtra(EXTRA_STABLE_DURATION_MS, reading.stableDurationMs)
        }
        context.sendBroadcast(intent)
    }

    companion object {
        const val ACTION_POSTURE_CHANGED =
            "com.paperplane.sleepsense.action.POSTURE_CHANGED"
        const val EXTRA_STATE = "state"
        const val EXTRA_FLATNESS = "flatness"
        const val EXTRA_STABLE_DURATION_MS = "stable_duration_ms"
    }
}
