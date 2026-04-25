package com.insurance.mobile.core.util

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import com.insurance.mobile.R
import com.insurance.mobile.core.network.dto.ExpiringWindowPolicyDto
import java.net.URLEncoder

/**
 * Default country code used when a number has no explicit international prefix. Kept as `+91`
 * because the app currently targets India only.
 */
private const val DEFAULT_COUNTRY_CODE = "+91"

/**
 * Normalises a raw phone string to E.164 form suitable for the system dialer
 * (`Intent.ACTION_DIAL` with a `tel:` URI).
 *
 * Rules:
 * - Already starts with `+` → keep the leading `+`, drop any other non-digit chars.
 *   Example: `+91 98765 43210` → `+919876543210`, `+1-415-555-2671` → `+14155552671`.
 * - 12 digits starting with `91` (no `+`) → prepend `+`. Example: `919876543210` → `+919876543210`.
 * - 11 digits starting with `0` (Indian trunk-prefixed) → drop the `0` and prepend `+91`.
 *   Example: `09876543210` → `+919876543210`.
 * - 10 digits → assume Indian mobile and prepend `+91`. Example: `9876543210` → `+919876543210`.
 * - Anything shorter than 10 digits → returned as `null` (caller should treat as invalid).
 * - Anything else (longer international numbers without `+`) → preserved with a leading `+`.
 *
 * Returns `null` for null/blank/non-numeric input or numbers too short to dial.
 */
fun formatPhoneNumberForDial(phone: String?): String? {
    if (phone.isNullOrBlank()) return null
    val trimmed = phone.trim()
    val hasPlus = trimmed.startsWith("+")
    val digits = buildString {
        for (c in trimmed) if (c.isDigit()) append(c)
    }
    if (digits.isEmpty()) return null

    return when {
        hasPlus -> "+$digits"
        digits.length == 10 -> "$DEFAULT_COUNTRY_CODE$digits"
        digits.length == 11 && digits.startsWith("0") ->
            "$DEFAULT_COUNTRY_CODE${digits.substring(1)}"
        digits.length == 12 && digits.startsWith("91") -> "+$digits"
        digits.length < 10 -> null
        else -> "+$digits"
    }
}

/**
 * Returns the digits-only form (no `+`) suitable for WhatsApp `wa.me/` URLs.
 * Internally reuses [formatPhoneNumberForDial] so the country-code rules stay consistent.
 */
fun formatPhoneNumberForWhatsApp(phone: String?): String? =
    formatPhoneNumberForDial(phone)?.removePrefix("+")

/**
 * Backward-compatible alias that returns the WhatsApp-friendly digits-only form.
 *
 * Historically this also served the dialer, which produced numbers like `919876543210`
 * (no `+`) that the dialer treated as invalid. New code should call
 * [formatPhoneNumberForDial] for `tel:` URIs and [formatPhoneNumberForWhatsApp] for
 * `wa.me` URIs explicitly.
 */
@Deprecated(
    message = "Use formatPhoneNumberForDial(...) for tel: URIs and " +
        "formatPhoneNumberForWhatsApp(...) for wa.me URIs.",
    replaceWith = ReplaceWith("formatPhoneNumberForWhatsApp(phone)"),
)
fun sanitizePhoneNumber(phone: String?): String? = formatPhoneNumberForWhatsApp(phone)

/** Opens the dialer with the given digits (does not place the call). */
fun getDialIntent(phoneDigits: String): Intent =
    Intent(Intent.ACTION_DIAL).apply {
        data = Uri.parse("tel:${Uri.encode(phoneDigits)}")
    }

fun buildWhatsAppUri(phoneDigits: String, message: String): Uri {
    val encoded = URLEncoder.encode(message, Charsets.UTF_8.name())
    return Uri.parse("https://wa.me/$phoneDigits?text=$encoded")
}

fun getWhatsAppIntent(phoneDigits: String, message: String): Intent =
    Intent(Intent.ACTION_VIEW, buildWhatsAppUri(phoneDigits, message))

fun buildWhatsAppRenewalMessage(
    item: ExpiringWindowPolicyDto,
    expiryFormatted: String,
    context: Context,
): String {
    val name = item.customerName?.trim().takeUnless { it.isNullOrEmpty() }
        ?: context.getString(R.string.renewal_window_whatsapp_name_fallback)
    val type = item.policyType?.trim().takeUnless { it.isNullOrEmpty() }
        ?: context.getString(R.string.renewal_window_whatsapp_placeholder)
    return context.getString(
        R.string.renewal_window_whatsapp_message_template,
        name,
        type.lowercase(),
        expiryFormatted,
    )
}

/**
 * Tries WhatsApp app first; if unavailable, opens the same [https://wa.me/...] URL in a browser.
 * Shows a short toast only if nothing can handle the URL.
 */
fun openWhatsAppWithFallback(context: Context, phoneDigits: String, message: String) {
    val base = getWhatsAppIntent(phoneDigits, message)
    val uri = base.data ?: return
    val whatsapp = Intent(base).apply { setPackage("com.whatsapp") }
    val pm = context.packageManager
    try {
        if (whatsapp.resolveActivity(pm) != null) {
            context.startActivity(whatsapp)
            return
        }
        val browser = Intent(Intent.ACTION_VIEW, uri)
        if (browser.resolveActivity(pm) != null) {
            context.startActivity(browser)
        } else {
            Toast.makeText(
                context,
                R.string.renewal_window_whatsapp_unavailable,
                Toast.LENGTH_SHORT,
            ).show()
        }
    } catch (_: ActivityNotFoundException) {
        Toast.makeText(
            context,
            R.string.renewal_window_whatsapp_unavailable,
            Toast.LENGTH_SHORT,
        ).show()
    }
}

fun safeStartDialer(context: Context, phoneDigits: String) {
    try {
        context.startActivity(getDialIntent(phoneDigits))
    } catch (_: ActivityNotFoundException) {
        Toast.makeText(
            context,
            R.string.renewal_window_dialer_unavailable,
            Toast.LENGTH_SHORT,
        ).show()
    }
}
