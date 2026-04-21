package com.insurance.mobile.feature.renewalwindow.data

import com.insurance.mobile.core.network.NetworkErrorMapper
import com.insurance.mobile.core.network.api.RenewalApi
import com.insurance.mobile.core.network.dto.ExpiringWindowPolicyDto
import com.insurance.mobile.feature.renewalwindow.domain.RenewalWindow
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class RenewalWindowRepository @Inject constructor(
    private val renewalApi: RenewalApi,
) {

    suspend fun loadExpiringPolicies(window: RenewalWindow): Result<List<ExpiringWindowPolicyDto>> =
        withContext(Dispatchers.IO) {
            try {
                Result.success(renewalApi.getExpiringList(window.routeArg))
            } catch (e: Exception) {
                Result.failure(Exception(NetworkErrorMapper.message(e)))
            }
        }
}
