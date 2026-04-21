package com.insurance.mobile.core.network.api

/**
 * Placeholder for a **future** dedicated expiring-policies HTTP API.
 *
 * **Current implementation:** The feature uses:
 * - [PolicyApi.getPolicies] — premium, insurer, payment status, dates, type
 * - [CustomerApi.getCustomers] — name, phone (joined by `customer_id`)
 *
 * **API ADJUSTMENT:** When the backend exposes a single endpoint (e.g. `GET /policies/expiring`),
 * add Retrofit methods here, register in DI, and switch [ExpiringPolicyRepository] to call it
 * instead of merging two lists.
 */
interface ExpiringPoliciesApi {
    // Example future contract:
    // @GET("policies/expiring")
    // suspend fun listExpiring(@Query("withinDays") withinDays: Int?): List<ExpiringPolicyRowDto>
}
