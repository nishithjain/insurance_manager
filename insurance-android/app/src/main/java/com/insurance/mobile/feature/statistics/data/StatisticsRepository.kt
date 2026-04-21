package com.insurance.mobile.feature.statistics.data

import com.insurance.mobile.core.network.NetworkErrorMapper
import com.insurance.mobile.core.network.api.StatisticsApi
import com.insurance.mobile.core.network.dto.DashboardStatisticsDto
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Read-only statistics — same payload as the web Statistics page (`GET /statistics/dashboard`).
 *
 * **API note:** If you split analytics into multiple endpoints later, replace [getDashboardStatistics]
 * with the new API shape and update [DashboardStatisticsDto] (or add new DTOs).
 */
@Singleton
class StatisticsRepository @Inject constructor(
    private val statisticsApi: StatisticsApi,
) {

    suspend fun getDashboardStatistics(): Result<DashboardStatisticsDto> = withContext(Dispatchers.IO) {
        try {
            Result.success(statisticsApi.getDashboardStatistics())
        } catch (e: Exception) {
            Result.failure(Exception(NetworkErrorMapper.message(e)))
        }
    }
}
