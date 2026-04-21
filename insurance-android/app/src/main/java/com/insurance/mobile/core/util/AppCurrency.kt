package com.insurance.mobile.core.util

import java.text.NumberFormat
import java.util.Locale

/**
 * Premium and payment amounts are INR, consistent with the web UI (₹).
 * Using [Locale.getDefault] for currency would show USD ($) on typical US-configured emulators.
 */
object AppCurrency {
    val formatter: NumberFormat =
        NumberFormat.getCurrencyInstance(Locale.forLanguageTag("en-IN"))
}
