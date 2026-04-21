package com.insurance.mobile.core.network

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Lightweight GET [baseUrl]health with short timeouts for startup / test connection.
 */
@Singleton
class ServerHealthChecker @Inject constructor() {

    private val client: OkHttpClient =
        OkHttpClient.Builder()
            .connectTimeout(CONNECT_SEC, TimeUnit.SECONDS)
            .readTimeout(READ_SEC, TimeUnit.SECONDS)
            .writeTimeout(READ_SEC, TimeUnit.SECONDS)
            .build()

    suspend fun checkReachable(apiBaseUrl: String): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val base = apiBaseUrl.trimEnd('/') + "/"
            val url = "${base}health"
            val request = Request.Builder().url(url).get().build()
            client.newCall(request).execute().use { response ->
                if (response.isSuccessful) {
                    Result.success(Unit)
                } else {
                    Result.failure(Exception("HTTP ${response.code}"))
                }
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    companion object {
        private const val CONNECT_SEC = 5L
        private const val READ_SEC = 8L
    }
}
