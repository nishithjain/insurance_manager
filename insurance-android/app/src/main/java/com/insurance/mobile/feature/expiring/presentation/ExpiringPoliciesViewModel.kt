package com.insurance.mobile.feature.expiring.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.insurance.mobile.feature.expiring.data.ExpiringPolicyRepository
import com.insurance.mobile.feature.expiring.domain.ExpiringPolicyItem
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class ExpiringPoliciesViewModel @Inject constructor(
    private val repository: ExpiringPolicyRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow<ExpiringPoliciesUiState>(ExpiringPoliciesUiState.Loading)
    val uiState: StateFlow<ExpiringPoliciesUiState> = _uiState.asStateFlow()

    private val _isRefreshing = MutableStateFlow(false)
    val isRefreshing: StateFlow<Boolean> = _isRefreshing.asStateFlow()

    private var cached: List<ExpiringPolicyItem> = emptyList()
    private var searchQuery: String = ""
    private var bucket: ExpiringBucket = ExpiringBucket.Within30

    init {
        load(initial = true)
    }

    fun load(initial: Boolean = false) {
        viewModelScope.launch {
            if (initial) {
                _uiState.value = ExpiringPoliciesUiState.Loading
            } else {
                _isRefreshing.value = true
            }
            try {
                repository.loadExpiringPolicies().fold(
                    onSuccess = { list ->
                        cached = list
                        applyFilters()
                    },
                    onFailure = { e ->
                        if (initial) {
                            _uiState.value = ExpiringPoliciesUiState.Error(e.message ?: "Error")
                        }
                        // Refresh failure: keep existing Success list; user can retry pull-to-refresh.
                    },
                )
            } finally {
                _isRefreshing.value = false
            }
        }
    }

    fun onSearchQueryChange(query: String) {
        searchQuery = query
        applyFilters()
    }

    fun onBucketChange(newBucket: ExpiringBucket) {
        bucket = newBucket
        applyFilters()
    }

    fun refresh() = load(initial = false)

    private fun applyFilters() {
        val q = searchQuery.trim().lowercase()
        val bucketFiltered = cached.filter { bucket.matches(it.daysLeft) }
        val searched = if (q.isEmpty()) {
            bucketFiltered
        } else {
            bucketFiltered.filter { row ->
                listOf(
                    row.customerName,
                    row.customerPhone,
                    row.policyNumber,
                    row.policyType,
                    row.insurerCompany,
                    row.paymentStatus,
                ).any { field -> field.lowercase().contains(q) }
            }
        }
        _uiState.value = ExpiringPoliciesUiState.Success(
            allItems = cached,
            visibleItems = searched,
            searchQuery = searchQuery,
            bucket = bucket,
        )
    }
}
