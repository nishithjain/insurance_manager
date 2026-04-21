package com.insurance.mobile.feature.policies.ui

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Inbox
import androidx.compose.material3.Button
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.MenuAnchorType
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.insurance.mobile.R
import com.insurance.mobile.ui.components.EmptyState
import com.insurance.mobile.ui.components.InsuranceFullScreenLoading
import com.insurance.mobile.ui.components.InsuranceTopBar
import com.insurance.mobile.feature.policies.presentation.PoliciesListUiState
import com.insurance.mobile.feature.policies.presentation.PoliciesListViewModel

/**
 * Read-only policy directory: search, type filter, lazy list; tap opens detail.
 *
 * **API:** List rows are built from `GET /policies` + `GET /customers` (see [PoliciesRepository]).
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PoliciesListScreen(
    onBack: () -> Unit,
    onPolicyClick: (policyId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: PoliciesListViewModel = hiltViewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            InsuranceTopBar(
                title = stringResource(R.string.policies_list_title),
                navigationIcon = {
                    androidx.compose.material3.TextButton(onClick = onBack) {
                        Text(stringResource(R.string.action_back))
                    }
                },
                actions = {
                    androidx.compose.material3.TextButton(onClick = { viewModel.refresh() }) {
                        Text(stringResource(R.string.action_refresh))
                    }
                },
            )
        },
    ) { padding ->
        when (val s = uiState) {
            PoliciesListUiState.Loading -> {
                InsuranceFullScreenLoading(
                    Modifier
                        .fillMaxSize()
                        .padding(padding),
                )
            }
            is PoliciesListUiState.Error -> {
                Column(
                    Modifier
                        .fillMaxSize()
                        .padding(padding)
                        .padding(24.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    Text(text = s.message, color = MaterialTheme.colorScheme.error)
                    Button(onClick = { viewModel.refresh() }) {
                        Text(stringResource(R.string.action_retry))
                    }
                }
            }
            is PoliciesListUiState.Success -> {
                PoliciesListContent(
                    modifier = Modifier.padding(padding),
                    state = s,
                    onSearchChange = viewModel::onSearchChange,
                    onTypeFilterChange = viewModel::onTypeFilterChange,
                    onPolicyClick = onPolicyClick,
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PoliciesListContent(
    state: PoliciesListUiState.Success,
    onSearchChange: (String) -> Unit,
    onTypeFilterChange: (String?) -> Unit,
    onPolicyClick: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    var typeMenuExpanded by remember { mutableStateOf(false) }
    val selectedLabel = state.typeFilter ?: stringResource(R.string.policies_filter_all_types)

    Column(
        modifier = modifier.fillMaxSize(),
    ) {
        OutlinedTextField(
            value = state.searchQuery,
            onValueChange = onSearchChange,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 10.dp),
            placeholder = { Text(stringResource(R.string.policies_search_hint)) },
            singleLine = true,
            shape = MaterialTheme.shapes.medium,
            keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Words),
        )

        ExposedDropdownMenuBox(
            expanded = typeMenuExpanded,
            onExpandedChange = { typeMenuExpanded = !typeMenuExpanded },
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 4.dp),
        ) {
            OutlinedTextField(
                value = selectedLabel,
                onValueChange = {},
                readOnly = true,
                label = { Text(stringResource(R.string.policies_filter_type_label)) },
                trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = typeMenuExpanded) },
                modifier = Modifier
                    .fillMaxWidth()
                    .menuAnchor(MenuAnchorType.PrimaryNotEditable, enabled = true),
            )
            ExposedDropdownMenu(
                expanded = typeMenuExpanded,
                onDismissRequest = { typeMenuExpanded = false },
            ) {
                DropdownMenuItem(
                    text = { Text(stringResource(R.string.policies_filter_all_types)) },
                    onClick = {
                        onTypeFilterChange(null)
                        typeMenuExpanded = false
                    },
                )
                state.policyTypes.forEach { t ->
                    DropdownMenuItem(
                        text = { Text(t) },
                        onClick = {
                            onTypeFilterChange(t)
                            typeMenuExpanded = false
                        },
                    )
                }
            }
        }

        if (state.visibleRows.isEmpty()) {
            EmptyState(
                message = stringResource(R.string.policies_empty),
                icon = Icons.Outlined.Inbox,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
            )
        } else {
            LazyColumn(
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
            ) {
                items(
                    items = state.visibleRows,
                    key = { it.policyId },
                ) { row ->
                    PolicyListRow(item = row, onClick = { onPolicyClick(row.policyId) })
                }
            }
        }
    }
}
