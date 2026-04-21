package com.insurance.mobile.feature.statistics.presentation

import com.insurance.mobile.core.network.dto.DashboardStatisticsDto

sealed interface StatisticsUiState {
    data object Loading : StatisticsUiState
    data class Error(val message: String) : StatisticsUiState
    data class Success(val data: DashboardStatisticsDto) : StatisticsUiState
}
