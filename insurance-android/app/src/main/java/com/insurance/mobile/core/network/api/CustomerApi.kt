package com.insurance.mobile.core.network.api

import com.insurance.mobile.core.network.dto.CustomerDto
import retrofit2.http.GET

/**
 * Customers for the logged-in user (use to resolve names for policy rows).
 */
interface CustomerApi {

    @GET("customers")
    suspend fun getCustomers(): List<CustomerDto>
}
