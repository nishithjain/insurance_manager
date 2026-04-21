package com.insurance.mobile.feature.renewalwindow.presentation

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.insurance.mobile.feature.renewalwindow.data.RenewalWindowRepository
import com.insurance.mobile.feature.renewalwindow.domain.RenewalWindow
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class RenewalWindowListViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val repository: RenewalWindowRepository,
) : ViewModel() {

    val window: RenewalWindow = RenewalWindow.fromRouteArg(
        savedStateHandle.get<String>("window") ?: "7",
    )

    private val _uiState = MutableStateFlow<RenewalWindowListUiState>(RenewalWindowListUiState.Loading)
    val uiState: StateFlow<RenewalWindowListUiState> = _uiState.asStateFlow()

    private val _searchQuery = MutableStateFlow("")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.value = RenewalWindowListUiState.Loading
            repository.loadExpiringPolicies(window).fold(
                onSuccess = { list ->
                    _uiState.value = RenewalWindowListUiState.Success(list)
                },
                onFailure = { e ->
                    _uiState.value = RenewalWindowListUiState.Error(e.message ?: "Failed to load")
                },
            )
        }
    }

    fun setSearchQuery(value: String) {
        _searchQuery.update { value }
    }
}
