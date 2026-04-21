package com.insurance.mobile.feature.policies.domain

/**
 * One row on the policies list (merged policy + customer for search/display).
 */
data class PolicyListItem(
    val policyId: String,
    val customerName: String,
    val customerPhone: String,
    val policyNumber: String,
    val policyType: String,
    val premium: Double,
    val endDateIso: String,
    val status: String,
)
