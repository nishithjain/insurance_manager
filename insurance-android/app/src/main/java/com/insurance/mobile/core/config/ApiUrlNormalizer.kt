package com.insurance.mobile.core.config

import okhttp3.HttpUrl.Companion.toHttpUrlOrNull

/**
 * Normalizes user input into a Retrofit-compatible API root ending with `/api/`.
 * Accepts e.g. `http://192.168.1.10:5000` or `http://host:5000/api`.
 */
object ApiUrlNormalizer {

    fun validate(raw: String): Boolean = tryNormalize(raw) != null

    /**
     * Returns normalized API base URL with trailing slash, or null if invalid.
     */
    fun tryNormalize(raw: String): String? {
        var s = raw.trim().trimEnd('/')
        if (s.isEmpty()) return null
        if (!s.startsWith("http://", ignoreCase = true) &&
            !s.startsWith("https://", ignoreCase = true)
        ) {
            s = "http://$s"
        }
        val url = s.toHttpUrlOrNull() ?: return null
        if (url.host.isBlank()) return null

        val lastSegment = url.pathSegments.lastOrNull()
        val alreadyApiRoot = lastSegment?.equals("api", ignoreCase = true) == true
        val withApi = if (alreadyApiRoot) s else "$s/api"
        val withSlash = withApi.trimEnd('/') + "/"
        return withSlash.toHttpUrlOrNull()?.toString()
    }

    fun requireNormalized(raw: String): String =
        tryNormalize(raw) ?: throw IllegalArgumentException("Invalid server URL")
}
