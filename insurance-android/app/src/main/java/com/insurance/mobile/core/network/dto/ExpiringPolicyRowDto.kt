package com.insurance.mobile.core.network.dto

/**
 * **API ADJUSTMENT — not wired to Retrofit yet.** Documents a plausible future row shape if the
 * backend adds e.g. `GET /policies/expiring` with denormalized customer + policy fields.
 *
 * **Current app behavior:** Rows are built in [com.insurance.mobile.feature.expiring.data.ExpiringPolicyRepository]
 * by merging [PolicyDto] + [CustomerDto] from existing list endpoints.
 */
data class ExpiringPolicyRowDto(
    val policyId: String,
    val customerName: String,
    val customerPhone: String?,
    val policyNumber: String,
    val policyType: String,
    val insurerCompany: String?,
    val premium: Double,
    val endDate: String,
    val daysLeft: Int,
    val paymentStatus: String?,
)
