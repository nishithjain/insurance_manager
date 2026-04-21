package com.insurance.mobile.feature.policies.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.insurance.mobile.feature.policies.data.PoliciesRepository
import com.insurance.mobile.feature.policies.domain.PolicyListItem
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class PoliciesListViewModel @Inject constructor(
    private val policiesRepository: PoliciesRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow<PoliciesListUiState>(PoliciesListUiState.Loading)
    val uiState: StateFlow<PoliciesListUiState> = _uiState.asStateFlow()

    private var cached: List<PolicyListItem> = emptyList()
    private var searchQuery: String = ""
    private var typeFilter: String? = null

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.value = PoliciesListUiState.Loading
            policiesRepository.loadPolicyListRows().fold(
                onSuccess = { rows ->
                    cached = rows
                    applyFilters()
                },
                onFailure = { e ->
                    _uiState.value = PoliciesListUiState.Error(e.message ?: "Error")
                },
            )
        }
    }

    fun onSearchChange(query: String) {
        searchQuery = query
        applyFilters()
    }

    fun onTypeFilterChange(type: String?) {
        typeFilter = type
        applyFilters()
    }

    private fun applyFilters() {
        val types = cached.map { it.policyType }.distinct().sorted()
        val q = searchQuery.trim().lowercase()
        var list = cached

        val tf = typeFilter
        if (!tf.isNullOrBlank()) {
            list = list.filter { it.policyType == tf }
        }

        list = if (q.isEmpty()) {
            list
        } else {
            list.filter { row ->
                listOf(
                    row.customerName,
                    row.customerPhone,
                    row.policyNumber,
                ).any { it.lowercase().contains(q) }
            }
        }

        _uiState.value = PoliciesListUiState.Success(
            allRows = cached,
            visibleRows = list,
            searchQuery = searchQuery,
            typeFilter = typeFilter,
            policyTypes = types,
        )
    }
}
