package com.voxshield.oem

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.util.Log

private const val TAG = "VoxShield.OemBattery"

/**
 * OemBatteryOptimizationHelper — manufacturer-specific deep links to battery
 * optimization / autostart settings.
 *
 * Background: Many OEM Android skins (Xiaomi MIUI, Oppo ColorOS, Vivo FuntouchOS,
 * Huawei EMUI, Samsung OneUI) have aggressive background app managers that can
 * terminate even foreground services with persistent notifications, unless the
 * user explicitly allowlists the app in the OEM's battery/autostart settings.
 *
 * These settings are NOT exposed through any standard Android API — they are OEM
 * proprietary. The intent actions and component names below are derived from the
 * patterns documented by the dontkillmyapp.com / DontKillMyApp open-source project
 * (MIT-licensed research into OEM kill behaviours).
 *
 * Strategy:
 *   1. Detect manufacturer via Build.MANUFACTURER
 *   2. Try OEM-specific Intent; if it resolves → launch it
 *   3. Fallback: standard ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS AOSP intent
 *   4. Final fallback: open generic App Info screen (user navigates manually)
 */
object OemBatteryOptimizationHelper {

    // ─── OEM profile data class ───────────────────────────────────────────────

    data class OemProfile(
        val manufacturerName: String,           // Display name
        val manufacturerKeywords: List<String>, // Build.MANUFACTURER patterns (lowercase)
        val instructions: String,               // User-facing instruction text
        val intentActions: List<IntentSpec>     // Ordered list of intents to try
    )

    data class IntentSpec(
        val action: String? = null,
        val packageName: String? = null,
        val className: String? = null,
        val extras: Map<String, String> = emptyMap()
    )

    // ─── OEM profiles ─────────────────────────────────────────────────────────

    private val OEM_PROFILES = listOf(

        OemProfile(
            manufacturerName = "Xiaomi / MIUI",
            manufacturerKeywords = listOf("xiaomi", "redmi", "poco"),
            instructions = "Go to Security app → Manage apps → VoxShield → Autostart → Enable.\n" +
                    "Also go to Battery Saver → Choose apps → VoxShield → No restrictions.",
            intentActions = listOf(
                IntentSpec(
                    action = "miui.intent.action.APP_PERM_EDITOR",
                    packageName = "com.miui.securitycenter",
                    className = "com.miui.permcenter.autostart.AutoStartManagementActivity"
                ),
                IntentSpec(
                    action = "miui.intent.action.POWER_HIDE_MODE_APP_LIST",
                    packageName = "com.miui.powerkeeper",
                    className = "com.miui.powerkeeper.ui.HideAppsContainerManagementActivity"
                )
            )
        ),

        OemProfile(
            manufacturerName = "Oppo / ColorOS",
            manufacturerKeywords = listOf("oppo", "realme"),
            instructions = "Go to Phone Manager → App Management → VoxShield → " +
                    "Autostart → Allow.\nAlso set Battery Optimization to \"Not optimized\".",
            intentActions = listOf(
                IntentSpec(
                    packageName = "com.coloros.safecenter",
                    className = "com.coloros.safecenter.startupapp.StartupAppListActivity"
                ),
                IntentSpec(
                    packageName = "com.oppo.safe",
                    className = "com.oppo.safe.permission.startup.StartupAppListActivity"
                )
            )
        ),

        OemProfile(
            manufacturerName = "Vivo / FuntouchOS",
            manufacturerKeywords = listOf("vivo"),
            instructions = "Go to iManager → App Management → Background App Refresh → " +
                    "VoxShield → Enable.\nAlso allow High background power consumption.",
            intentActions = listOf(
                IntentSpec(
                    packageName = "com.iqoo.secure",
                    className = "com.iqoo.secure.ui.phoneoptimize.AddWhiteListActivity"
                ),
                IntentSpec(
                    packageName = "com.vivo.permissionmanager",
                    className = "com.vivo.permissionmanager.activity.BgStartUpManagerActivity"
                )
            )
        ),

        OemProfile(
            manufacturerName = "Huawei / EMUI / HarmonyOS",
            manufacturerKeywords = listOf("huawei", "honor"),
            instructions = "Go to Phone Manager → Protected apps → Enable VoxShield.\n" +
                    "Also go to Settings → Battery → App Launch → VoxShield → " +
                    "Disable Auto-manage, enable Run in background.",
            intentActions = listOf(
                IntentSpec(
                    packageName = "com.huawei.systemmanager",
                    className = "com.huawei.systemmanager.optimize.process.ProtectActivity"
                ),
                IntentSpec(
                    packageName = "com.huawei.systemmanager",
                    className = "com.huawei.systemmanager.startupmgr.ui.StartupNormalAppListActivity"
                )
            )
        ),

        OemProfile(
            manufacturerName = "Samsung / OneUI",
            manufacturerKeywords = listOf("samsung"),
            instructions = "Go to Settings → Device Care → Battery → Background usage limits " +
                    "→ Never sleeping apps → Add VoxShield.\n" +
                    "Also disable Battery optimization for VoxShield.",
            intentActions = listOf(
                IntentSpec(
                    packageName = "com.samsung.android.lool",
                    className = "com.samsung.android.sm.battery.ui.BatteryActivity"
                ),
                IntentSpec(
                    action = Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
                    extras = mapOf("package" to "{appPackage}")
                )
            )
        ),

        OemProfile(
            manufacturerName = "OnePlus / OxygenOS",
            manufacturerKeywords = listOf("oneplus"),
            instructions = "Go to Settings → Battery → Battery Optimization → VoxShield " +
                    "→ Don't optimize.\nOnePlus is generally less restrictive than other OEMs.",
            intentActions = listOf(
                IntentSpec(
                    action = Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
                    extras = mapOf("package" to "{appPackage}")
                )
            )
        )
    )

    // ─── Detection & launch ───────────────────────────────────────────────────

    /**
     * Returns the OEM profile matching the current device, or null if the device
     * is stock Android / unknown OEM with no special handling needed.
     */
    fun detectOemProfile(): OemProfile? {
        val manufacturer = Build.MANUFACTURER.lowercase()
        return OEM_PROFILES.firstOrNull { profile ->
            profile.manufacturerKeywords.any { keyword -> manufacturer.contains(keyword) }
        }
    }

    /**
     * Returns true if this device has a known aggressive battery manager that can
     * kill foreground services and requires the user to manually allowlist the app.
     */
    fun isRestrictiveOem(): Boolean = detectOemProfile() != null

    /**
     * Attempts to launch the OEM battery settings deep link.
     * Tries each IntentSpec in order; falls back to AOSP battery optimization
     * dialog, then falls back to App Info screen.
     *
     * @return true if any intent was successfully launched
     */
    fun launchBatterySettings(activity: Activity): Boolean {
        val packageName = activity.packageName
        val profile = detectOemProfile()

        // Try OEM-specific intents
        if (profile != null) {
            for (spec in profile.intentActions) {
                if (tryLaunchIntent(activity, spec, packageName)) {
                    Log.i(TAG, "Launched OEM battery settings for ${profile.manufacturerName}")
                    return true
                }
            }
        }

        // Fallback 1: AOSP Doze exemption dialog
        try {
            val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                data = Uri.parse("package:$packageName")
            }
            activity.startActivity(intent)
            Log.i(TAG, "Launched AOSP battery optimization dialog")
            return true
        } catch (e: Exception) {
            Log.w(TAG, "AOSP battery optimization dialog not available: ${e.message}")
        }

        // Fallback 2: App Info screen — user navigates manually
        try {
            val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                data = Uri.parse("package:$packageName")
            }
            activity.startActivity(intent)
            Log.i(TAG, "Launched App Info (final fallback)")
            return true
        } catch (e: Exception) {
            Log.e(TAG, "Could not open any settings screen: ${e.message}")
        }

        return false
    }

    private fun tryLaunchIntent(context: Context, spec: IntentSpec, packageName: String): Boolean {
        return try {
            val intent = Intent().apply {
                spec.action?.let { action = it }
                spec.className?.let { clazz ->
                    spec.packageName?.let { pkg ->
                        setClassName(pkg, clazz)
                    }
                } ?: spec.packageName?.let { pkg ->
                    `package` = pkg
                }
                spec.extras.forEach { (key, value) ->
                    putExtra(key, value.replace("{appPackage}", packageName))
                }
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            if (context.packageManager.resolveActivity(intent, 0) != null) {
                context.startActivity(intent)
                true
            } else {
                false
            }
        } catch (e: Exception) {
            Log.d(TAG, "Intent failed (expected): ${e.message}")
            false
        }
    }

    /**
     * Returns manufacturer-specific user-facing instruction text, or generic
     * instructions if this is a non-restrictive OEM.
     */
    fun getInstructions(context: Context): String {
        val profile = detectOemProfile()
        return profile?.instructions
            ?: "Go to Settings → Battery → Battery Optimization → VoxShield → Don't optimize."
    }
}
