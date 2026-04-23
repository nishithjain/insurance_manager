package com.insurance.mobile.feature.startup

import androidx.lifecycle.ViewModel
import com.insurance.mobile.core.auth.AuthTokenStore
import com.insurance.mobile.core.config.ServerConfigRepository
import com.insurance.mobile.core.network.ServerHealthChecker
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject

/**
 * Where to send the user after the splash resolves.
 *
 * Decision order:
 *   1. No saved / reachable server URL → ServerSetup.
 *   2. Server reachable but no stored JWT → Login.
 *   3. Everything OK → Main.
 */
enum class StartupDestination {
    Main,
    ServerSetup,
    Login,
}

@HiltViewModel
class StartupViewModel @Inject constructor(
    private val serverConfigRepository: ServerConfigRepository,
    private val serverHealthChecker: ServerHealthChecker,
    private val authTokenStore: AuthTokenStore,
) : ViewModel() {

    suspend fun resolveDestination(): StartupDestination {
        return try {
            val url = serverConfigRepository.hydrate()
            if (url.isNullOrBlank()) {
                return StartupDestination.ServerSetup
            }
            val reachable = serverHealthChecker.checkReachable(url).isSuccess
            if (!reachable) {
                return StartupDestination.ServerSetup
            }
            val session = authTokenStore.hydrate()
            if (session == null || session.token.isBlank()) {
                StartupDestination.Login
            } else {
                StartupDestination.Main
            }
        } catch (_: Exception) {
            StartupDestination.ServerSetup
        }
    }
}
