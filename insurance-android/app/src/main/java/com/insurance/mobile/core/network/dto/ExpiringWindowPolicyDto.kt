package com.insurance.mobile.core.network.dto

import com.squareup.moshi.Json

/**
 * One row from [GET /renewals/expiring-list] — matches dashboard renewal window counts.
 */
data class ExpiringWindowPolicyDto(
    val id: Int,
    @Json(name = "policy_number") val policyNumber: String?,
    @Json(name = "end_date") val endDate: String?,
    val premium: Double?,
    @Json(name = "policy_type") val policyType: String?,
    @Json(name = "customer_name") val customerName: String?,
    @Json(name = "customer_phone") val customerPhone: String?,
    @Json(name = "days_left") val daysLeft: Int,
)
