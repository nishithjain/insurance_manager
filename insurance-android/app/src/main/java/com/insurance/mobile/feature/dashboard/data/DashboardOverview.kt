package com.insurance.mobile.feature.dashboard.data

import com.insurance.mobile.core.network.dto.DashboardStatisticsDto
import com.insurance.mobile.core.network.dto.RenewalSummaryDto

/**
 * Aggregated data for the home dashboard.
 */
data class DashboardOverview(
    val statistics: DashboardStatisticsDto,
    val renewalSummary: RenewalSummaryDto,
)
