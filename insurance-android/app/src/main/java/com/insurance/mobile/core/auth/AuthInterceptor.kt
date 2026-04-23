package com.insurance.mobile.core.auth

import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

/**
 * OkHttp interceptor that:
 *   1. Attaches ``Authorization: Bearer <jwt>`` to every outbound API call
 *      that isn't itself an auth endpoint.
 *   2. Clears the cached session and notifies listeners when the server
 *      replies with 401 / 403 so the UI can redirect to login.
 *
 * Auth endpoints (``/auth/google``, ``/auth/logout``) are exempt from the
 * Authorization header so a stale/invalid token never blocks the user from
 * re-logging in.
 */
@Singleton
class AuthInterceptor @Inject constructor(
    private val tokenStore: AuthTokenStore,
    private val unauthorizedRelay: UnauthorizedRelay,
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()
        val path = original.url.encodedPath

        val skipAuthHeader =
            path.endsWith("/auth/google") || path.endsWith("/auth/logout")

        val token = tokenStore.getCachedSession()?.token
        val request = if (!skipAuthHeader && !token.isNullOrBlank()) {
            original.newBuilder()
                .header("Authorization", "Bearer $token")
                .build()
        } else {
            original
        }

        val response = chain.proceed(request)

        if (response.code == 401 || response.code == 403) {
            runBlocking { tokenStore.clear() }
            unauthorizedRelay.signal(response.code)
        }

        return response
    }
}
