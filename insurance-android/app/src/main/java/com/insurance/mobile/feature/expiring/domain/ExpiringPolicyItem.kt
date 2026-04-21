package com.insurance.mobile.feature.expiring.domain

/**
 * One row in the expiring-policies list (UI + domain). Built from merged API DTOs.
 */
data class ExpiringPolicyItem(
    val policyId: String,
    val customerName: String,
    val customerPhone: String,
    val policyNumber: String,
    val policyType: String,
    val insurerCompany: String,
    val premium: Double,
    /** ISO `yyyy-MM-dd` preferred for display formatting in UI */
    val endDateIso: String,
    val daysLeft: Int,
    val paymentStatus: String,
)
