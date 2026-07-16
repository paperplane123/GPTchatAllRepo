package com.paperplane.sleepsense

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.paperplane.sleepsense.automation.AutomationDispatcher
import com.paperplane.sleepsense.sensor.LieDownState
import com.paperplane.sleepsense.sensor.PostureReading
import com.paperplane.sleepsense.sensor.PostureSensorController

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MaterialTheme {
                SleepSenseScreen()
            }
        }
    }
}

@Composable
private fun SleepSenseScreen() {
    val context = LocalContext.current.applicationContext
    var reading by remember { mutableStateOf(PostureReading()) }
    var state by remember { mutableStateOf(LieDownState.UPRIGHT) }
    val dispatcher = remember(context) { AutomationDispatcher(context) }
    val controller = remember(context) {
        PostureSensorController(
            context = context,
            onReading = { reading = it },
            onStateChanged = { newState, newReading ->
                state = newState
                dispatcher.dispatch(newState, newReading)
            },
        )
    }

    DisposableEffect(controller) {
        controller.start()
        onDispose { controller.stop() }
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .systemBarsPadding()
                .padding(24.dp),
            verticalArrangement = Arrangement.Center,
        ) {
            Text(
                text = "SleepSense",
                style = MaterialTheme.typography.headlineLarge,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = "公开传感器版躺下姿态代理检测",
                style = MaterialTheme.typography.bodyLarge,
            )

            Spacer(modifier = Modifier.height(24.dp))

            StateCard(state = state, reading = reading)

            Spacer(modifier = Modifier.height(20.dp))

            Text(
                text = "测试方法",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                text = "将手机从竖直姿态缓慢转为屏幕近似水平，保持稳定约 8 秒。进入 LYING_STABLE 后会发送自定义 Android 广播。",
                style = MaterialTheme.typography.bodyMedium,
            )

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = "注意：当前识别的是手机姿态，不是直接识别人体是否躺下。",
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}

@Composable
private fun StateCard(
    state: LieDownState,
    reading: PostureReading,
) {
    val stateDescription = when (state) {
        LieDownState.UPRIGHT -> "未进入候选姿态"
        LieDownState.CANDIDATE -> "姿态符合，等待稳定"
        LieDownState.LYING_STABLE -> "已触发躺下姿态事件"
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.padding(20.dp),
        ) {
            Text(
                text = state.name,
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = stateDescription,
                style = MaterialTheme.typography.bodyLarge,
            )

            Spacer(modifier = Modifier.height(16.dp))

            MetricLine("屏幕平面倾角", "%.1f°".format(reading.tiltFromHorizontalDegrees))
            MetricLine("平放置信度", "%.3f".format(reading.flatness))
            MetricLine("陀螺仪角速度", "%.3f rad/s".format(reading.gyroMagnitudeRadPerSec))
            MetricLine("稳定持续时间", "%.1f s".format(reading.stableDurationMs / 1000f))
            MetricLine(
                "姿态传感器",
                if (reading.usingAccelerometerFallback) "加速度计回退" else "重力传感器",
            )
        }
    }
}

@Composable
private fun MetricLine(label: String, value: String) {
    Text(
        text = "$label：$value",
        style = MaterialTheme.typography.bodyMedium,
    )
}
