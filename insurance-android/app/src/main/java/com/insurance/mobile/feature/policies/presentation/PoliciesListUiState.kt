package com.insurance.mobile.feature.policies.presentation

import com.insurance.mobile.feature.policies.domain.PolicyListItem

sealed interface PoliciesListUiState {
    data object Loading : PoliciesListUiState
    data class Error(val message: String) : PoliciesListUiState
    data class Success(
        val allRows: List<PolicyListItem>,
        val visibleRows: List<PolicyListItem>,
        val searchQuery: String,
        /** `null` means all types */
        val typeFilter: String?,
        val policyTypes: List<String>,
    ) : PoliciesListUiState
}
