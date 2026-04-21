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
 * Strips spaces, brackets, hyphens, and non-digits. If the result is exactly 10 digits (typical
 * Indian mobile without country code), prepends `91` for WhatsApp (`wa.me`) compatibility.
 */
fun sanitizePhoneNumber(phone: String?): String? {
    if (phone.isNullOrBlank()) return null
    val digits = buildString {
        for (c in phone) {
            if (c.isDigit()) append(c)
        }
    }
    if (digits.isEmpty()) return null
    return when {
        digits.length == 10 -> "91$digits"
        else -> digits
    }
}

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
    val policyNo = item.policyNumber?.trim().takeUnless { it.isNullOrEmpty() }
        ?: context.getString(R.string.renewal_window_whatsapp_placeholder)
    return context.getString(
        R.string.renewal_window_whatsapp_message_template,
        name,
        type,
        policyNo,
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
