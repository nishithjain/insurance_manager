package com.insurance.mobile.core.network.dto

import com.squareup.moshi.Json

/**
 * Matches backend [User] model.
 */
data class UserDto(
    @Json(name = "user_id") val userId: String,
    val email: String,
    val name: String? = null,
    val picture: String? = null,
    @Json(name = "created_at") val createdAt: String,
)
