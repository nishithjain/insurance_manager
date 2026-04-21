package com.insurance.mobile.core.network.api

import com.insurance.mobile.core.network.dto.DashboardStatisticsDto
import retrofit2.http.GET

/**
 * Aggregated KPIs for dashboard / statistics screens.
 */
interface StatisticsApi {

    @GET("statistics/dashboard")
    suspend fun getDashboardStatistics(): DashboardStatisticsDto
}
