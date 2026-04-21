package com.insurance.mobile.feature.policies.data

import com.insurance.mobile.core.network.NetworkErrorMapper
import com.insurance.mobile.core.network.api.CustomerApi
import com.insurance.mobile.core.network.api.PolicyApi
import com.insurance.mobile.core.network.dto.PolicyDetailResponseDto
import com.insurance.mobile.feature.policies.domain.PolicyListItem
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Read-only policies list (merged from policies + customers) and enriched detail bundle.
 */
@Singleton
class PoliciesRepository @Inject constructor(
    private val policyApi: PolicyApi,
    private val customerApi: CustomerApi,
) {

    suspend fun loadPolicyListRows(): Result<List<PolicyListItem>> = withContext(Dispatchers.IO) {
        try {
            val policies = policyApi.getPolicies()
            val customers = customerApi.getCustomers().associateBy { it.id }
            val rows = policies.mapNotNull { p ->
                val c = customers[p.customerId] ?: return@mapNotNull null
                PolicyListItem(
                    policyId = p.id,
                    customerName = c.name,
                    customerPhone = c.phone?.takeIf { it.isNotBlank() } ?: "—",
                    policyNumber = p.policyNumber,
                    policyType = p.policyType,
                    premium = p.premium,
                    endDateIso = p.endDate,
                    status = p.status,
                )
            }.sortedWith(
                compareBy<PolicyListItem> { it.endDateIso }.thenBy { it.policyNumber },
            )
            Result.success(rows)
        } catch (e: Exception) {
            Result.failure(Exception(NetworkErrorMapper.message(e)))
        }
    }

    suspend fun getPolicyDetail(policyId: String): Result<PolicyDetailResponseDto> =
        withContext(Dispatchers.IO) {
            try {
                Result.success(policyApi.getPolicyDetail(policyId))
            } catch (e: Exception) {
                Result.failure(Exception(NetworkErrorMapper.message(e)))
            }
        }
}
