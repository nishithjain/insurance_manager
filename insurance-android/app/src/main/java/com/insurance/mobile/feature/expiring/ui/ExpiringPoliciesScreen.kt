package com.insurance.mobile.feature.expiring.ui

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Inbox
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.pulltorefresh.PullToRefreshState
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.insurance.mobile.R
import com.insurance.mobile.feature.expiring.presentation.ExpiringBucket
import com.insurance.mobile.feature.expiring.presentation.ExpiringPoliciesUiState
import com.insurance.mobile.feature.expiring.presentation.ExpiringPoliciesViewModel
import com.insurance.mobile.ui.components.EmptyState
import com.insurance.mobile.ui.components.InsuranceFullScreenLoading
import com.insurance.mobile.ui.components.InsuranceTopBar

/**
 * Expiring policies list with search, day-bucket filters, and pull-to-refresh.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ExpiringPoliciesScreen(
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ExpiringPoliciesViewModel = hiltViewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val isRefreshing by viewModel.isRefreshing.collectAsStateWithLifecycle()
    val pullState = rememberPullToRefreshState()

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            InsuranceTopBar(
                title = stringResource(R.string.expiring_title),
                navigationIcon = {
                    androidx.compose.material3.TextButton(onClick = onBack) {
                        Text(stringResource(R.string.action_back))
                    }
                },
            )
        },
    ) { padding ->
        when (val s = uiState) {
            ExpiringPoliciesUiState.Loading -> {
                InsuranceFullScreenLoading(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding),
                )
            }
            is ExpiringPoliciesUiState.Error -> {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding)
                        .padding(24.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    Text(text = s.message, color = MaterialTheme.colorScheme.error)
                    Button(onClick = { viewModel.load(initial = true) }) {
                        Text(stringResource(R.string.action_retry))
                    }
                }
            }
            is ExpiringPoliciesUiState.Success -> {
                ExpiringPoliciesContent(
                    modifier = Modifier.padding(padding),
                    state = s,
                    isRefreshing = isRefreshing,
                    pullState = pullState,
                    onRefresh = { viewModel.refresh() },
                    onSearchChange = viewModel::onSearchQueryChange,
                    onBucketChange = viewModel::onBucketChange,
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ExpiringPoliciesContent(
    state: ExpiringPoliciesUiState.Success,
    isRefreshing: Boolean,
    pullState: PullToRefreshState,
    onRefresh: () -> Unit,
    onSearchChange: (String) -> Unit,
    onBucketChange: (ExpiringBucket) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier.fillMaxSize()) {
        OutlinedTextField(
            value = state.searchQuery,
            onValueChange = onSearchChange,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 10.dp),
            placeholder = { Text(stringResource(R.string.expiring_search_hint)) },
            singleLine = true,
            shape = MaterialTheme.shapes.medium,
            keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.None),
        )

        BucketChipRow(
            selected = state.bucket,
            onSelect = onBucketChange,
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState())
                .padding(horizontal = 12.dp, vertical = 6.dp),
        )

        PullToRefreshBox(
            isRefreshing = isRefreshing,
            onRefresh = onRefresh,
            state = pullState,
            modifier = Modifier.fillMaxSize(),
        ) {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                if (state.visibleItems.isEmpty()) {
                    item {
                        EmptyState(
                            message = stringResource(R.string.expiring_empty),
                            icon = Icons.Outlined.Inbox,
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 48.dp),
                        )
                    }
                } else {
                    items(
                        items = state.visibleItems,
                        key = { it.policyId },
                    ) { item ->
                        ExpiringPolicyRow(item = item)
                    }
                }
            }
        }
    }
}

@Composable
private fun BucketChipRow(
    selected: ExpiringBucket,
    onSelect: (ExpiringBucket) -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        BucketChip(
            label = stringResource(R.string.bucket_today),
            selected = selected == ExpiringBucket.Today,
            onClick = { onSelect(ExpiringBucket.Today) },
        )
        BucketChip(
            label = stringResource(R.string.bucket_7),
            selected = selected == ExpiringBucket.Within7,
            onClick = { onSelect(ExpiringBucket.Within7) },
        )
        BucketChip(
            label = stringResource(R.string.bucket_15),
            selected = selected == ExpiringBucket.Within15,
            onClick = { onSelect(ExpiringBucket.Within15) },
        )
        BucketChip(
            label = stringResource(R.string.bucket_30),
            selected = selected == ExpiringBucket.Within30,
            onClick = { onSelect(ExpiringBucket.Within30) },
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun BucketChip(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
) {
    FilterChip(
        selected = selected,
        onClick = onClick,
        label = { Text(label) },
        shape = MaterialTheme.shapes.small,
        colors = FilterChipDefaults.filterChipColors(
            selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
            selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer,
        ),
    )
}
