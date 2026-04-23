package com.insurance.mobile.core.auth

import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import javax.inject.Inject
import javax.inject.Singleton

/**
 * One-way signal from the network layer to the UI: "the server just told us
 * the caller isn't authenticated anymore (401/403) — kick them back to login."
 *
 * Exposed as a hot [SharedFlow] so anywhere in the composable tree can listen
 * once and react, without the interceptor knowing anything about the nav graph.
 */
@Singleton
class UnauthorizedRelay @Inject constructor() {
    private val _events = MutableSharedFlow<Int>(
        replay = 0,
        extraBufferCapacity = 4,
        onBufferOverflow = BufferOverflow.DROP_OLDEST,
    )
    val events: SharedFlow<Int> = _events.asSharedFlow()

    fun signal(httpStatus: Int) {
        _events.tryEmit(httpStatus)
    }
}
