package com.insurance.mobile.feature.policies.presentation

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.insurance.mobile.feature.policies.data.PoliciesRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class PolicyDetailViewModel @Inject constructor(
    private val policiesRepository: PoliciesRepository,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {

    private val policyId: String =
        checkNotNull(savedStateHandle.get<String>("policyId")) { "policyId required" }

    private val _uiState = MutableStateFlow<PolicyDetailUiState>(PolicyDetailUiState.Loading)
    val uiState: StateFlow<PolicyDetailUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = PolicyDetailUiState.Loading
            policiesRepository.getPolicyDetail(policyId).fold(
                onSuccess = { _uiState.value = PolicyDetailUiState.Success(it) },
                onFailure = { e ->
                    _uiState.value = PolicyDetailUiState.Error(e.message ?: "Error")
                },
            )
        }
    }
}
