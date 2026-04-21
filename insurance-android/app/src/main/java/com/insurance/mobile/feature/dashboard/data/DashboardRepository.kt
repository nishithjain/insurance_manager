package com.insurance.mobile.feature.dashboard.data

import com.insurance.mobile.core.network.NetworkErrorMapper
import com.insurance.mobile.core.network.api.RenewalApi
import com.insurance.mobile.core.network.api.StatisticsApi
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Loads dashboard metrics from [StatisticsApi] and [RenewalApi] (renewal summary counts).
 */
@Singleton
class DashboardRepository @Inject constructor(
    private val statisticsApi: StatisticsApi,
    private val renewalApi: RenewalApi,
) {

    suspend fun loadOverview(): Result<DashboardOverview> = withContext(Dispatchers.IO) {
        try {
            val stats = statisticsApi.getDashboardStatistics()
            val reminders = renewalApi.getRenewalReminders()
            Result.success(
                DashboardOverview(
                    statistics = stats,
                    renewalSummary = reminders.summary,
                ),
            )
        } catch (e: Exception) {
            Result.failure(Exception(NetworkErrorMapper.message(e)))
        }
    }
}
