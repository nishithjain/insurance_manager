package com.insurance.mobile.feature.expiring.data

import com.insurance.mobile.core.network.NetworkErrorMapper
import com.insurance.mobile.core.network.api.CustomerApi
import com.insurance.mobile.core.network.api.PolicyApi
import com.insurance.mobile.core.util.daysUntilExpiry
import com.insurance.mobile.core.util.parsePolicyEndDate
import com.insurance.mobile.feature.expiring.domain.ExpiringPolicyItem
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.time.ZoneId
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Builds expiring policy rows by merging [PolicyApi] + [CustomerApi].
 *
 * **API ADJUSTMENT:**
 * - Includes only policies with `status == active` (case-insensitive) and `end_date >= today`
 *   (calendar). If the backend uses different semantics, adjust filtering.
 * - Phone / company / payment come from policy + customer DTOs; if a field is missing in JSON,
 *   we show an em dash in the UI layer via [ExpiringPolicyItem] strings.
 */
@Singleton
class ExpiringPolicyRepository @Inject constructor(
    private val policyApi: PolicyApi,
    private val customerApi: CustomerApi,
) {

    suspend fun loadExpiringPolicies(): Result<List<ExpiringPolicyItem>> = withContext(Dispatchers.IO) {
        try {
            val policies = policyApi.getPolicies()
            val customers = customerApi.getCustomers()
            val byCustomerId = customers.associateBy { it.id }

            val items = policies.mapNotNull { policy ->
                if (!policy.status.equals("active", ignoreCase = true)) return@mapNotNull null
                val end = parsePolicyEndDate(policy.endDate) ?: return@mapNotNull null
                val daysLeft = daysUntilExpiry(end, ZoneId.systemDefault())
                if (daysLeft < 0) return@mapNotNull null

                val customer = byCustomerId[policy.customerId] ?: return@mapNotNull null

                ExpiringPolicyItem(
                    policyId = policy.id,
                    customerName = customer.name,
                    customerPhone = customer.phone?.takeIf { it.isNotBlank() } ?: "—",
                    policyNumber = policy.policyNumber,
                    policyType = policy.policyType,
                    insurerCompany = policy.insurerCompany?.takeIf { it.isNotBlank() } ?: "—",
                    premium = policy.premium,
                    endDateIso = end.toString(),
                    daysLeft = daysLeft.toInt(),
                    paymentStatus = policy.paymentStatus?.takeIf { it.isNotBlank() } ?: "—",
                )
            }.sortedWith(compareBy({ it.daysLeft }, { it.policyNumber }))

            Result.success(items)
        } catch (e: Exception) {
            Result.failure(Exception(NetworkErrorMapper.message(e)))
        }
    }
}
