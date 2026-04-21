package com.insurance.mobile.core.network.dto

import com.squareup.moshi.Json

/**
 * Matches backend [Customer] model.
 */
data class CustomerDto(
    val id: String,
    @Json(name = "user_id") val userId: String,
    val name: String,
    val email: String? = null,
    val phone: String? = null,
    val address: String? = null,
    @Json(name = "created_at") val createdAt: String,
)
