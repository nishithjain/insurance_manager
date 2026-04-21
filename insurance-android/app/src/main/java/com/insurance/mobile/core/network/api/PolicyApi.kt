package com.insurance.mobile.core.network.api

import com.insurance.mobile.core.network.dto.PolicyDetailResponseDto
import com.insurance.mobile.core.network.dto.PolicyDto
import retrofit2.http.GET
import retrofit2.http.Path

/**
 * Read-only policy list + detail for the logged-in user.
 */
interface PolicyApi {

    @GET("policies")
    suspend fun getPolicies(): List<PolicyDto>

    @GET("policies/{id}")
    suspend fun getPolicy(@Path("id") policyId: String): PolicyDto

    /** Policy + customer + motor/health/property blocks when present (backend v2 detail bundle). */
    @GET("policies/{id}/detail")
    suspend fun getPolicyDetail(@Path("id") policyId: String): PolicyDetailResponseDto
}
