package com.insurance.mobile.feature.renewalwindow.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Inbox
import androidx.compose.material.icons.outlined.SearchOff
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.insurance.mobile.R
import com.insurance.mobile.core.network.dto.ExpiringWindowPolicyDto
import com.insurance.mobile.core.util.AppCurrency
import com.insurance.mobile.core.util.buildWhatsAppRenewalMessage
import com.insurance.mobile.core.util.formatPhoneNumberForDial
import com.insurance.mobile.core.util.formatPhoneNumberForWhatsApp
import com.insurance.mobile.core.util.openWhatsAppWithFallback
import com.insurance.mobile.core.util.parsePolicyEndDate
import com.insurance.mobile.core.util.safeStartDialer
import com.insurance.mobile.feature.renewalwindow.presentation.RenewalWindowListUiState
import com.insurance.mobile.feature.renewalwindow.presentation.RenewalWindowListViewModel
import com.insurance.mobile.ui.components.ContactActionButtonRow
import com.insurance.mobile.ui.components.EmptyState
import com.insurance.mobile.ui.components.ExpiryStatusBadge
import com.insurance.mobile.ui.components.InsuranceFullScreenLoading
import com.insurance.mobile.ui.components.InsuranceTopBar
import java.time.format.DateTimeFormatter
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RenewalWindowListScreen(
    onBack: () -> Unit,
    onPolicyClick: (policyId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: RenewalWindowListViewModel = hiltViewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val searchQuery by viewModel.searchQuery.collectAsStateWithLifecycle()
    val window = viewModel.window

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            InsuranceTopBar(
                title = stringResource(window.screenTitleRes),
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
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
        ) {
            OutlinedTextField(
                value = searchQuery,
                onValueChange = viewModel::setSearchQuery,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 10.dp),
                placeholder = { Text(stringResource(R.string.renewal_window_search_hint)) },
                singleLine = true,
                shape = MaterialTheme.shapes.medium,
            )

            when (val s = uiState) {
                RenewalWindowListUiState.Loading -> {
                    InsuranceFullScreenLoading(modifier = Modifier.fillMaxSize())
                }
                is RenewalWindowListUiState.Error -> {
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(24.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp),
                    ) {
                        Text(text = s.message, color = MaterialTheme.colorScheme.error)
                        Button(onClick = { viewModel.refresh() }) {
                            Text(stringResource(R.string.action_retry))
                        }
                    }
                }
                is RenewalWindowListUiState.Success -> {
                    val filtered = remember(s.items, searchQuery) {
                        filterBySearch(s.items, searchQuery)
                    }
                    if (filtered.isEmpty()) {
                        EmptyState(
                            message = if (s.items.isEmpty()) {
                                stringResource(window.emptyMessageRes)
                            } else {
                                stringResource(R.string.renewal_window_search_no_results)
                            },
                            icon = if (s.items.isEmpty()) Icons.Outlined.Inbox else Icons.Outlined.SearchOff,
                            modifier = Modifier.fillMaxSize(),
                        )
                    } else {
                        LazyColumn(
                            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            items(filtered, key = { it.id }) { item ->
                                ExpiringWindowPolicyCard(
                                    item = item,
                                    onPolicyClick = { onPolicyClick(item.id.toString()) },
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

private fun filterBySearch(
    items: List<ExpiringWindowPolicyDto>,
    query: String,
): List<ExpiringWindowPolicyDto> {
    val q = query.trim().lowercase()
    if (q.isEmpty()) return items
    return items.filter { item ->
        item.customerName?.lowercase()?.contains(q) == true ||
            item.customerPhone?.lowercase()?.contains(q) == true
    }
}

@Composable
private fun ExpiringWindowPolicyCard(
    item: ExpiringWindowPolicyDto,
    onPolicyClick: () -> Unit,
) {
    val context = LocalContext.current
    val dateFmt = remember { DateTimeFormatter.ofPattern("d MMMM uuuu", Locale.ENGLISH) }
    val expiryLabel = remember(item.endDate) {
        val d = parsePolicyEndDate(item.endDate)
        if (d != null) dateFmt.format(d) else (item.endDate ?: "—")
    }
    val premiumLabel = item.premium?.let { AppCurrency.formatter.format(it) } ?: "—"
    val dialNumber = remember(item.customerPhone) { formatPhoneNumberForDial(item.customerPhone) }
    val whatsAppNumber = remember(item.customerPhone) {
        formatPhoneNumberForWhatsApp(item.customerPhone)
    }
    val phoneDisplay = item.customerPhone?.trim().takeUnless { it.isNullOrEmpty() } ?: "—"

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.large,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top,
            ) {
                Text(
                    text = item.customerName?.trim().takeUnless { it.isNullOrEmpty() } ?: "—",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier
                        .weight(1f)
                        .clickable(onClick = onPolicyClick)
                        .padding(end = 8.dp),
                )
                ExpiryStatusBadge(daysLeft = item.daysLeft)
            }

            Text(
                text = item.policyType?.trim().takeUnless { it.isNullOrEmpty() } ?: "—",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column {
                    Text(
                        text = stringResource(R.string.renewal_window_field_premium),
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        text = premiumLabel,
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Medium,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        text = stringResource(R.string.renewal_window_field_expiry),
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        text = expiryLabel,
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Medium,
                    )
                }
            }

            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.6f))

            if (dialNumber != null) {
                Text(
                    text = "${stringResource(R.string.renewal_window_field_phone)}: $phoneDisplay",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.clickable {
                        safeStartDialer(context, dialNumber)
                    },
                )
            } else {
                Text(
                    text = "${stringResource(R.string.renewal_window_field_phone)}: $phoneDisplay",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            if (dialNumber != null) {
                ContactActionButtonRow(
                    callLabel = stringResource(R.string.renewal_window_action_call),
                    whatsAppLabel = stringResource(R.string.renewal_window_action_whatsapp),
                    onCall = { safeStartDialer(context, dialNumber) },
                    onWhatsApp = {
                        val target = whatsAppNumber ?: return@ContactActionButtonRow
                        val message = buildWhatsAppRenewalMessage(item, expiryLabel, context)
                        openWhatsAppWithFallback(context, target, message)
                    },
                )
            }
        }
    }
}
