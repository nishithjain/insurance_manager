package com.insurance.mobile.feature.startup

import androidx.lifecycle.ViewModel
import com.insurance.mobile.core.config.ServerConfigRepository
import com.insurance.mobile.core.network.ServerHealthChecker
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject

enum class StartupDestination {
    Main,
    ServerSetup,
}

@HiltViewModel
class StartupViewModel @Inject constructor(
    private val serverConfigRepository: ServerConfigRepository,
    private val serverHealthChecker: ServerHealthChecker,
) : ViewModel() {

    suspend fun resolveDestination(): StartupDestination {
        return try {
            val url = serverConfigRepository.hydrate()
            if (url.isNullOrBlank()) {
                return StartupDestination.ServerSetup
            }
            serverHealthChecker.checkReachable(url).fold(
                onSuccess = { StartupDestination.Main },
                onFailure = { StartupDestination.ServerSetup },
            )
        } catch (_: Exception) {
            StartupDestination.ServerSetup
        }
    }
}
