package com.insurance.mobile.core.util

import java.util.Locale

/**
 * Short INR for large amounts (e.g. ₹15.4L, ₹2.1Cr); smaller amounts use full currency formatting.
 */
object InrCompactFormat {
    fun format(amount: Double): String {
        if (amount.isNaN() || amount < 0) return AppCurrency.formatter.format(0.0)
        return when {
            amount >= 10_000_000.0 -> {
                val v = amount / 10_000_000.0
                "₹${String.format(Locale.US, "%.1f", v)}Cr"
            }
            amount >= 100_000.0 -> {
                val v = amount / 100_000.0
                "₹${String.format(Locale.US, "%.1f", v)}L"
            }
            else -> AppCurrency.formatter.format(amount)
        }
    }
}
