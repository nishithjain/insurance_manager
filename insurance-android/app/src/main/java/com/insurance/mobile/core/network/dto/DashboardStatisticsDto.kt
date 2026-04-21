package com.insurance.mobile.core.network.dto

import com.squareup.moshi.Json

/**
 * Matches JSON from `GET /statistics/dashboard` (backend `build_dashboard_statistics`).
 *
 * **API ADJUSTMENT:** If the FastAPI response adds/removes fields, update this file and any
 * UI that reads those properties.
 */
data class DashboardStatisticsDto(
    @Json(name = "payment_received_this_month") val paymentReceivedThisMonth: Double,
    @Json(name = "pending_payments_count") val pendingPaymentsCount: Int,
    @Json(name = "pending_payments_amount") val pendingPaymentsAmount: Double,
    @Json(name = "renewals_this_month") val renewalsThisMonth: Int,
    @Json(name = "expiring_this_month") val expiringThisMonth: Int,
    @Json(name = "renewal_conversion_rate") val renewalConversionRate: Double?,
    @Json(name = "expired_not_renewed_open") val expiredNotRenewedOpen: Int,
    @Json(name = "total_customers") val totalCustomers: Int,
    @Json(name = "total_policies") val totalPolicies: Int? = null,
    @Json(name = "repeat_customers") val repeatCustomers: Int,
    @Json(name = "monthly_trend") val monthlyTrend: List<MonthlyTrendDto>,
    @Json(name = "policy_type_distribution") val policyTypeDistribution: List<PolicyTypeCountDto>,
    @Json(name = "as_of_date") val asOfDate: String,
    @Json(name = "current_month_label") val currentMonthLabel: String,
)

data class MonthlyTrendDto(
    val month: String,
    @Json(name = "payments_received") val paymentsReceived: Double,
    val renewals: Int,
    val expiring: Int,
)

data class PolicyTypeCountDto(
    @Json(name = "policy_type") val policyType: String,
    val count: Int,
)
