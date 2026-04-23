package com.insurance.mobile.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.insurance.mobile.core.auth.AuthSession
import com.insurance.mobile.core.auth.AuthTokenStore
import com.insurance.mobile.core.auth.UnauthorizedRelay
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.SharingStarted
import javax.inject.Inject

/**
 * Cross-cutting root state: current auth session + unauthorized events.
 *
 * Keeps [InsuranceRoot] a thin view function while still giving it live
 * visibility into auth changes from anywhere in the app.
 */
@HiltViewModel
class RootViewModel @Inject constructor(
    tokenStore: AuthTokenStore,
    unauthorizedRelay: UnauthorizedRelay,
) : ViewModel() {
    val session: StateFlow<AuthSession?> = tokenStore.sessionFlow
        .stateIn(viewModelScope, SharingStarted.Eagerly, tokenStore.getCachedSession())
    val unauthorizedEvents: SharedFlow<Int> = unauthorizedRelay.events
}
