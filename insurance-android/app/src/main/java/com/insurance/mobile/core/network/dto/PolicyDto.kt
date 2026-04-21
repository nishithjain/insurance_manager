package com.insurance.mobile.core.network.dto

import com.squareup.moshi.Json

/**
 * Matches backend [Policy] model (list + detail use the same shape).
 */
data class PolicyDto(
    val id: String,
    @Json(name = "user_id") val userId: String,
    @Json(name = "customer_id") val customerId: String,
    @Json(name = "policy_number") val policyNumber: String,
    @Json(name = "policy_type") val policyType: String,
    @Json(name = "insurer_company") val insurerCompany: String? = null,
    @Json(name = "payment_status") val paymentStatus: String? = null,
    @Json(name = "payment_note") val paymentNote: String? = null,
    @Json(name = "payment_updated_at") val paymentUpdatedAt: String? = null,
    @Json(name = "start_date") val startDate: String,
    @Json(name = "end_date") val endDate: String,
    val premium: Double,
    val status: String,
    @Json(name = "created_at") val createdAt: String,
    @Json(name = "last_contacted_at") val lastContactedAt: String? = null,
    @Json(name = "contact_status") val contactStatus: String = "Not Contacted",
    @Json(name = "follow_up_date") val followUpDate: String? = null,
    @Json(name = "renewal_status") val renewalStatus: String = "Open",
    @Json(name = "renewal_resolution_note") val renewalResolutionNote: String? = null,
    @Json(name = "renewal_resolved_at") val renewalResolvedAt: String? = null,
    @Json(name = "renewal_resolved_by") val renewalResolvedBy: String? = null,
)
