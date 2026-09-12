package com.voxshield

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.os.Bundle
import android.os.IBinder
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.*
import com.voxshield.audio.AudioCaptureManager
import com.voxshield.service.DEFAULT_BACKEND_WS_URL
import com.voxshield.service.ProtectionState
import com.voxshield.service.VoxShieldForegroundService
import com.voxshield.ui.screens.HomeScreen
import com.voxshield.ui.screens.OemBatteryGuideScreen
import com.voxshield.ui.screens.OnboardingScreen
import com.voxshield.ui.theme.VoxShieldTheme
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    private var foregroundService: VoxShieldForegroundService? = null
    private var isBound = false

    // Live state from the bound service (or defaults if not bound)
    private val _protectionState = MutableStateFlow(ProtectionState())
    private val _audioAmplitude = MutableStateFlow(0f)
    
    // UI routing state
    private val _showOnboarding = MutableStateFlow(false)
    private val _showOemGuide = MutableStateFlow(false)

    private val connection = object : ServiceConnection {
        override fun onServiceConnected(className: ComponentName, service: IBinder) {
            val binder = service as VoxShieldForegroundService.LocalBinder
            foregroundService = binder.service
            isBound = true

            // Connect UI flows to Service flows
            lifecycleScope.launch {
                binder.service.protectionState.collect { state ->
                    _protectionState.value = state
                }
            }
        }

        override fun onServiceDisconnected(arg0: ComponentName) {
            isBound = false
            foregroundService = null
            _protectionState.value = ProtectionState()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val prefs = getSharedPreferences(VoxShieldForegroundService.PREFS_NAME, MODE_PRIVATE)
        val onboardingDone = prefs.getBoolean(VoxShieldForegroundService.PREF_ONBOARDING_DONE, false)
        val backendUrl = prefs.getString(VoxShieldForegroundService.PREF_BACKEND_URL, DEFAULT_BACKEND_WS_URL) ?: DEFAULT_BACKEND_WS_URL

        _showOnboarding.value = !onboardingDone

        setContent {
            VoxShieldTheme {
                val showOnboarding by _showOnboarding.collectAsState()
                val showOemGuide by _showOemGuide.collectAsState()
                val protectionState by _protectionState.collectAsState()
                val amplitude by _audioAmplitude.collectAsState()

                when {
                    showOnboarding -> {
                        OnboardingScreen(
                            onComplete = {
                                prefs.edit().putBoolean(VoxShieldForegroundService.PREF_ONBOARDING_DONE, true).apply()
                                _showOnboarding.value = false
                                // Check if we need to show OEM guide
                                if (com.voxshield.oem.OemBatteryOptimizationHelper.isRestrictiveOem()) {
                                    _showOemGuide.value = true
                                }
                            },
                            onSkip = {
                                prefs.edit().putBoolean(VoxShieldForegroundService.PREF_ONBOARDING_DONE, true).apply()
                                _showOnboarding.value = false
                            }
                        )
                    }
                    showOemGuide -> {
                        OemBatteryGuideScreen(
                            onContinue = {
                                _showOemGuide.value = false
                            }
                        )
                    }
                    else -> {
                        HomeScreen(
                            protectionState = protectionState,
                            amplitude = amplitude,
                            backendUrl = backendUrl,
                            onBackendUrlChange = { newUrl ->
                                prefs.edit().putString(VoxShieldForegroundService.PREF_BACKEND_URL, newUrl).apply()
                                // If protection is active, we should restart the service to apply the new URL
                                if (protectionState.isProtectionActive) {
                                    val intent = Intent(this@MainActivity, VoxShieldForegroundService::class.java).apply {
                                        action = VoxShieldForegroundService.ACTION_START
                                        putExtra(VoxShieldForegroundService.EXTRA_BACKEND_URL, newUrl)
                                    }
                                    startForegroundService(intent)
                                }
                            },
                            onDismissAlert = {
                                foregroundService?.dismissAlert()
                            }
                        )
                    }
                }
            }
        }
    }

    override fun onStart() {
        super.onStart()
        // Bind to service to get real-time state updates for UI
        Intent(this, VoxShieldForegroundService::class.java).also { intent ->
            bindService(intent, connection, Context.BIND_AUTO_CREATE)
        }
    }

    override fun onStop() {
        super.onStop()
        if (isBound) {
            unbindService(connection)
            isBound = false
            foregroundService = null
        }
    }
}
