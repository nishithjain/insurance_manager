package com.insurance.mobile.core.network.dto

/**
 * Generic FastAPI error body: `{"detail": "..."}` or validation errors (we show a generic message if parse fails).
 */
data class FastApiErrorDto(
    val detail: String? = null,
)
