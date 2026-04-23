package com.insurance.mobile.core.network.api

import com.insurance.mobile.core.network.dto.AppUserDto
import com.insurance.mobile.core.network.dto.DevLoginRequest
import com.insurance.mobile.core.network.dto.GoogleLoginRequest
import com.insurance.mobile.core.network.dto.TokenResponseDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

/**
 * Auth endpoints. The backend trades a Google ID token for its own short-lived
 * JWT; all subsequent calls must carry that JWT in ``Authorization: Bearer``.
 */
interface AuthApi {
    @POST("auth/google")
    suspend fun loginWithGoogle(@Body body: GoogleLoginRequest): TokenResponseDto

    /** Dev-only shortcut. Returns 404 unless backend has ALLOW_DEV_AUTH=true. */
    @POST("auth/dev-login")
    suspend fun loginDev(@Body body: DevLoginRequest): TokenResponseDto

    @GET("auth/me")
    suspend fun me(): AppUserDto

    @POST("auth/logout")
    suspend fun logout(): Map<String, String>
}
