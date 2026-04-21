package com.insurance.mobile.feature.expiring.presentation

/**
 * Inclusive day windows from today: **0 = expires today**.
 *
 * - [Today] — only policies expiring today
 * - [Within7] — `0 <= daysLeft <= 7`
 * - [Within15] — `0 <= daysLeft <= 15`
 * - [Within30] — `0 <= daysLeft <= 30`
 *
 * **API ADJUSTMENT:** If you need non-overlapping buckets (e.g. 1–7 excluding today), change
 * [matchesBucket] in [ExpiringPoliciesViewModel].
 */
enum class ExpiringBucket {
    Today,
    Within7,
    Within15,
    Within30,
    ;

    fun matches(daysLeft: Int): Boolean = when (this) {
        Today -> daysLeft == 0
        Within7 -> daysLeft in 0..7
        Within15 -> daysLeft in 0..15
        Within30 -> daysLeft in 0..30
    }
}
