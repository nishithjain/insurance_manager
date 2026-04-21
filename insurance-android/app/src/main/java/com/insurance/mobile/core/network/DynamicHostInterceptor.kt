package com.insurance.mobile.core.network

import com.insurance.mobile.core.config.ServerConfigRepository
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.Interceptor
import okhttp3.Response
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Rewrites the request host to match [ServerConfigRepository]'s saved API base URL.
 * Retrofit uses a fixed placeholder base; only scheme, host, and port are replaced — path is unchanged.
 */
@Singleton
class DynamicHostInterceptor @Inject constructor(
    private val serverConfigRepository: ServerConfigRepository,
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val configured = serverConfigRepository.getCachedBaseUrl()
            ?: throw IOException("Server address is not configured")

        val target = configured.toHttpUrlOrNull()
            ?: throw IOException("Invalid stored server address")

        val original = chain.request()
        val url = original.url
        val newUrl = url.newBuilder()
            .scheme(target.scheme)
            .host(target.host)
            .port(target.port)
            .build()

        return chain.proceed(
            original.newBuilder().url(newUrl).build(),
        )
    }
}
