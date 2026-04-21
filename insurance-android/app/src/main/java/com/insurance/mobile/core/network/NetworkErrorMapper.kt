package com.insurance.mobile.core.network

import com.insurance.mobile.core.network.dto.FastApiErrorDto
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import retrofit2.HttpException
import java.io.IOException

/**
 * Turns Retrofit/IO errors into short user-facing strings for Snackbars / Text.
 */
object NetworkErrorMapper {

    private val moshi: Moshi = Moshi.Builder()
        .addLast(KotlinJsonAdapterFactory())
        .build()

    private val errorAdapter = moshi.adapter(FastApiErrorDto::class.java)

    fun message(throwable: Throwable): String = when (throwable) {
        is HttpException -> {
            val body = throwable.response()?.errorBody()?.string()
            parseFastApiDetail(body) ?: "Error ${throwable.code()}: ${throwable.message()}"
        }
        is IOException -> "Network error. Check your connection and API base URL."
        else -> throwable.message ?: "Something went wrong."
    }

    private fun parseFastApiDetail(json: String?): String? {
        if (json.isNullOrBlank()) return null
        return try {
            errorAdapter.fromJson(json)?.detail?.takeIf { it.isNotBlank() }
        } catch (_: Exception) {
            null
        }
    }
}
