package com.insurance.mobile.core.network.dto

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

/** Body of POST /api/auth/google. */
@JsonClass(generateAdapter = true)
data class GoogleLoginRequest(
    @Json(name = "id_token") val idToken: String,
)

/** Body of POST /api/auth/dev-login (only honored when backend sets ALLOW_DEV_AUTH=true). */
@JsonClass(generateAdapter = true)
data class DevLoginRequest(
    @Json(name = "email") val email: String,
)

/** Response of POST /api/auth/google. */
@JsonClass(generateAdapter = true)
data class TokenResponseDto(
    @Json(name = "access_token") val accessToken: String,
    @Json(name = "token_type") val tokenType: String,
    @Json(name = "expires_at") val expiresAt: String,
    @Json(name = "user") val user: AppUserDto,
)

/** Shape returned by /auth/me and /users endpoints. */
@JsonClass(generateAdapter = true)
data class AppUserDto(
    @Json(name = "id") val id: Int,
    @Json(name = "email") val email: String,
    @Json(name = "full_name") val fullName: String,
    @Json(name = "role") val role: String,
    @Json(name = "is_active") val isActive: Boolean,
    @Json(name = "created_at") val createdAt: String,
    @Json(name = "updated_at") val updatedAt: String,
    @Json(name = "created_by") val createdBy: Int? = null,
    @Json(name = "last_login_at") val lastLoginAt: String? = null,
)
