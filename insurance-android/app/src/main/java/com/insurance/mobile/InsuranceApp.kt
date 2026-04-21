package com.insurance.mobile

import android.app.Application
import com.insurance.mobile.core.config.ServerConfigRepository
import dagger.hilt.android.HiltAndroidApp
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * Application entry point for Hilt.
 * Preloads saved server URL so networking works after process restore without visiting Startup.
 */
@HiltAndroidApp
class InsuranceApp : Application() {

    @Inject
    lateinit var serverConfigRepository: ServerConfigRepository

    private val appScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onCreate() {
        super.onCreate()
        appScope.launch {
            serverConfigRepository.hydrate()
        }
    }
}
