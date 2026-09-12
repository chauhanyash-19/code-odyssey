package com.voxshield.call

import android.content.Context
import android.database.Cursor
import android.net.Uri
import android.provider.ContactsContract
import android.util.Log
import com.voxshield.util.PermissionUtils

private const val TAG = "VoxShield.ContactLookup"

/**
 * ContactLookupHelper — checks whether an incoming phone number is saved in the user's contacts.
 *
 * ──────────────────────────────────────────────────────────────────────────────
 * PURPOSE: Used solely to decide whether to show the prominent "Unknown number
 *          — Start Protection?" banner. This is a user-experience filter, not
 *          a security gate. Protection can always be started manually.
 *
 * PRIVACY GUARANTEES:
 *  ✅ Uses ContactsContract.PhoneLookup — the standard, minimal API for this.
 *     PhoneLookup only answers "does this number exist in contacts?" — it does
 *     NOT return contact names, emails, photos, or any other personal data
 *     unless explicitly queried (we do not query those columns).
 *  ✅ No contact data is stored, logged, or transmitted.
 *  ✅ Result is used only transiently to set the UI prompt visibility flag.
 *
 * FAIL-OPEN POLICY:
 *  If READ_CONTACTS is denied → returns false (unknown) → prompt is ALWAYS
 *  shown. We never silently hide the protection prompt due to a missing
 *  permission.
 *
 * API COMPATIBILITY:
 *  ContactsContract.PhoneLookup is available from API 5 and requires only
 *  READ_CONTACTS (a standard, non-restricted permission).
 * ──────────────────────────────────────────────────────────────────────────────
 */
object ContactLookupHelper {

    /**
     * Check whether [phoneNumber] matches any saved contact.
     *
     * @param context   Application or service context.
     * @param phoneNumber  Raw phone number string (may include country code, spaces, dashes).
     *                     If null or blank → treated as unknown (returns false).
     * @return true if the number is found in the user's saved contacts; false otherwise.
     *         Returns false on permission denial (fail-open toward showing the prompt).
     */
    fun isKnownContact(context: Context, phoneNumber: String?): Boolean {
        if (phoneNumber.isNullOrBlank()) {
            Log.d(TAG, "No phone number available — treating as unknown (fail-open)")
            return false
        }

        // Fail-open: if permission is denied, treat as unknown so prompt is always shown
        if (!PermissionUtils.hasReadContacts(context)) {
            Log.d(TAG, "READ_CONTACTS denied — treating $phoneNumber as unknown (fail-open)")
            return false
        }

        var cursor: Cursor? = null
        return try {
            val lookupUri: Uri = Uri.withAppendedPath(
                ContactsContract.PhoneLookup.CONTENT_FILTER_URI,
                Uri.encode(phoneNumber)
            )
            // Only request the _ID column — we don't need any personal data,
            // just whether at least one row exists
            cursor = context.contentResolver.query(
                lookupUri,
                arrayOf(ContactsContract.PhoneLookup._ID),
                null,
                null,
                null
            )
            val found = (cursor?.count ?: 0) > 0
            Log.d(TAG, "Contact lookup for $phoneNumber: found=$found")
            found
        } catch (e: Exception) {
            // Any content-provider error → fail-open (unknown)
            Log.w(TAG, "Contact lookup failed for $phoneNumber: ${e.message} — treating as unknown")
            false
        } finally {
            cursor?.close()
        }
    }
}
