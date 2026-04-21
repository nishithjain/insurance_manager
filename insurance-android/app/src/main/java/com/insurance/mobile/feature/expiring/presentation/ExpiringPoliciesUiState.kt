package com.insurance.mobile.feature.expiring.presentation

import com.insurance.mobile.feature.expiring.domain.ExpiringPolicyItem

sealed interface ExpiringPoliciesUiState {
    data object Loading : ExpiringPoliciesUiState
    data class Error(val message: String) : ExpiringPoliciesUiState
    data class Success(
        val allItems: List<ExpiringPolicyItem>,
        val visibleItems: List<ExpiringPolicyItem>,
        val searchQuery: String,
        val bucket: ExpiringBucket,
    ) : ExpiringPoliciesUiState
}
