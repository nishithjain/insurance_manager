package com.insurance.mobile.feature.dashboard.presentation

import com.insurance.mobile.feature.dashboard.data.DashboardOverview

sealed interface DashboardUiState {
    data object Loading : DashboardUiState
    data class Error(val message: String) : DashboardUiState
    data class Success(val overview: DashboardOverview) : DashboardUiState
}
