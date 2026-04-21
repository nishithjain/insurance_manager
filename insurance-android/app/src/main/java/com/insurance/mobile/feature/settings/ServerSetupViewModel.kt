package com.insurance.mobile.feature.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.insurance.mobile.core.config.ApiUrlNormalizer
import com.insurance.mobile.core.config.ServerConfigRepository
import com.insurance.mobile.core.network.ServerHealthChecker
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ServerSetupUiState(
    val input: String = "",
    val busy: Boolean = false,
    val error: String? = null,
    val statusMessage: String? = null,
)

@HiltViewModel
class ServerSetupViewModel @Inject constructor(
    private val serverConfigRepository: ServerConfigRepository,
    private val serverHealthChecker: ServerHealthChecker,
) : ViewModel() {

    private val _uiState = MutableStateFlow(ServerSetupUiState())
    val uiState: StateFlow<ServerSetupUiState> = _uiState.asStateFlow()

    init {
        serverConfigRepository.getCachedBaseUrl()?.let { cached ->
            _uiState.update {
                it.copy(input = cached.trimEnd('/'))
            }
        }
    }

    fun onInputChange(value: String) {
        _uiState.update {
            it.copy(input = value, error = null, statusMessage = null)
        }
    }

    fun testConnection() {
        val raw = _uiState.value.input.trim()
        if (raw.isEmpty()) {
            _uiState.update { it.copy(statusMessage = "Enter a server address first") }
            return
        }
        val normalized = ApiUrlNormalizer.tryNormalize(raw)
        if (normalized == null) {
            _uiState.update { it.copy(error = "Please enter a valid address") }
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(busy = true, error = null, statusMessage = null) }
            val result = serverHealthChecker.checkReachable(normalized)
            _uiState.update {
                it.copy(
                    busy = false,
                    statusMessage = result.fold(
                        onSuccess = { "Connection successful" },
                        onFailure = { e -> "Unable to connect: ${e.message ?: "unknown error"}" },
                    ),
                    error = if (result.isFailure) "Unable to connect to server" else null,
                )
            }
        }
    }

    /**
     * Saves the URL, verifies health, then invokes [onSuccess] only if the server responds.
     */
    fun saveAndContinue(onSuccess: () -> Unit) {
        val raw = _uiState.value.input.trim()
        if (raw.isEmpty()) {
            _uiState.update { it.copy(error = "Please enter a valid address") }
            return
        }
        if (!ApiUrlNormalizer.validate(raw)) {
            _uiState.update { it.copy(error = "Please enter a valid http or https URL") }
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(busy = true, error = null, statusMessage = null) }
            serverConfigRepository.saveBaseUrl(raw).fold(
                onSuccess = { normalized ->
                    val health = serverHealthChecker.checkReachable(normalized)
                    if (health.isSuccess) {
                        _uiState.update {
                            it.copy(busy = false, statusMessage = "Server address saved successfully")
                        }
                        onSuccess()
                    } else {
                        _uiState.update {
                            it.copy(
                                busy = false,
                                error = "Unable to connect to server. Check the address or your network.",
                                statusMessage = health.exceptionOrNull()?.message,
                            )
                        }
                    }
                },
                onFailure = { e ->
                    _uiState.update {
                        it.copy(busy = false, error = e.message ?: "Could not save")
                    }
                },
            )
        }
    }

    /**
     * Saves without requiring a successful health check (e.g. user knows server is temporarily down).
     */
    fun saveWithoutHealthCheck(onSuccess: () -> Unit) {
        val raw = _uiState.value.input.trim()
        if (raw.isEmpty()) {
            _uiState.update { it.copy(error = "Please enter a valid address") }
            return
        }
        if (!ApiUrlNormalizer.validate(raw)) {
            _uiState.update { it.copy(error = "Please enter a valid http or https URL") }
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(busy = true, error = null, statusMessage = null) }
            serverConfigRepository.saveBaseUrl(raw).fold(
                onSuccess = {
                    _uiState.update {
                        it.copy(busy = false, statusMessage = "Server address saved")
                    }
                    onSuccess()
                },
                onFailure = { e ->
                    _uiState.update {
                        it.copy(busy = false, error = e.message ?: "Could not save")
                    }
                },
            )
        }
    }
}
