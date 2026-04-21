package com.insurance.mobile.core.network.dto

import com.squareup.moshi.Json

/**
 * GET /renewals/reminders — bucketed active policies by days until [end_date].
 */
data class RenewalRemindersDto(
    val today: List<ReminderPolicyDto> = emptyList(),
    @Json(name = "day_1") val day1: List<ReminderPolicyDto> = emptyList(),
    @Json(name = "day_7") val day7: List<ReminderPolicyDto> = emptyList(),
    @Json(name = "day_15") val day15: List<ReminderPolicyDto> = emptyList(),
    @Json(name = "day_30") val day30: List<ReminderPolicyDto> = emptyList(),
    @Json(name = "day_31_to_90") val day31To90: List<ReminderPolicyDto> = emptyList(),
    @Json(name = "day_91_to_365") val day91To365: List<ReminderPolicyDto> = emptyList(),
    val summary: RenewalSummaryDto,
)

data class RenewalSummaryDto(
    @Json(name = "expiring_today") val expiringToday: Int? = null,
    @Json(name = "expiring_within_7_days") val expiringWithin7Days: Int,
    @Json(name = "expiring_within_15_days") val expiringWithin15Days: Int,
    @Json(name = "expiring_within_30_days") val expiringWithin30Days: Int,
    @Json(name = "expiring_within_365_days") val expiringWithin365Days: Int,
    val expired: Int,
)

/**
 * One row inside each reminder bucket (slim fields from the SQL SELECT).
 */
data class ReminderPolicyDto(
    val id: Int,
    @Json(name = "policy_number") val policyNumber: String?,
    @Json(name = "end_date") val endDate: String?,
    @Json(name = "start_date") val startDate: String?,
    val premium: Double?,
    val status: String?,
    @Json(name = "policy_type") val policyType: String?,
    @Json(name = "customer_name") val customerName: String?,
    @Json(name = "customer_email") val customerEmail: String?,
)
