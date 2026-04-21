package com.insurance.mobile.feature.policies.presentation

import com.insurance.mobile.core.network.dto.PolicyDetailResponseDto

sealed interface PolicyDetailUiState {
    data object Loading : PolicyDetailUiState
    data class Error(val message: String) : PolicyDetailUiState
    data class Success(val detail: PolicyDetailResponseDto) : PolicyDetailUiState
}
