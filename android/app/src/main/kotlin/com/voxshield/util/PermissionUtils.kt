package com.voxshield.util

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat

/**
 * PermissionUtils — unified permission check helpers.
 *
 * Centralises the API-level branching for phone state permissions:
 *   READ_PHONE_STATE      : required on API 26–32
 *   READ_BASIC_PHONE_STATE: preferred on API 33+ (less privileged — no carrier info)
 *
 * Note: We request both in the manifest and at runtime to ensure maximum
 * compatibility across OEMs that backport API 33 permission behaviour.
 */
object PermissionUtils {

    /** @return true if RECORD_AUDIO has been granted. */
    fun hasRecordAudio(context: Context): Boolean =
        ContextCompat.checkSelfPermission(
            context, Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED

    /**
     * @return true if the appropriate phone-state permission is granted.
     * On API 33+ checks READ_BASIC_PHONE_STATE; on lower APIs checks READ_PHONE_STATE.
     */
    fun hasPhoneState(context: Context): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ContextCompat.checkSelfPermission(
                context, Manifest.permission.READ_BASIC_PHONE_STATE
            ) == PackageManager.PERMISSION_GRANTED
        } else {
            ContextCompat.checkSelfPermission(
                context, Manifest.permission.READ_PHONE_STATE
            ) == PackageManager.PERMISSION_GRANTED
        }
    }

    /**
     * Returns the correct phone-state permission string for this Android version.
     * Use this as the argument to ActivityResultContracts.RequestPermission.
     */
    fun phoneStatePermission(): String =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            Manifest.permission.READ_BASIC_PHONE_STATE
        } else {
            Manifest.permission.READ_PHONE_STATE
        }

    /** @return true if POST_NOTIFICATIONS permission is needed and granted (API 33+). */
    fun hasPostNotifications(context: Context): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return true // Not required below API 33
        return ContextCompat.checkSelfPermission(
            context, Manifest.permission.POST_NOTIFICATIONS
        ) == PackageManager.PERMISSION_GRANTED
    }

    /** @return true if all permissions required for full protection are granted. */
    fun hasAllRequiredPermissions(context: Context): Boolean =
        hasRecordAudio(context) && hasPostNotifications(context)

    /** @return true if RECORD_AUDIO and phone state permissions are both granted. */
    fun hasFullPermissions(context: Context): Boolean =
        hasRecordAudio(context) && hasPhoneState(context) && hasPostNotifications(context)

    /**
     * @return true if READ_CONTACTS permission is granted.
     *
     * This is an optional permission — the app degrades gracefully if denied
     * (unknown-caller detection falls back to treating all callers as unknown,
     * which means the protection prompt is shown for all calls — fail-open).
     */
    fun hasReadContacts(context: Context): Boolean =
        ContextCompat.checkSelfPermission(
            context, Manifest.permission.READ_CONTACTS
        ) == PackageManager.PERMISSION_GRANTED
}
