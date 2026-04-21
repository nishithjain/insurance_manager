package com.insurance.mobile.feature.renewalwindow.presentation

import com.insurance.mobile.core.network.dto.ExpiringWindowPolicyDto

sealed interface RenewalWindowListUiState {
    data object Loading : RenewalWindowListUiState
    data class Success(val items: List<ExpiringWindowPolicyDto>) : RenewalWindowListUiState
    data class Error(val message: String) : RenewalWindowListUiState
}
