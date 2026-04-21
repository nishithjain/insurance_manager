package com.insurance.mobile.feature.dashboard.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.ErrorOutline
import androidx.compose.material.icons.outlined.Event
import androidx.compose.material.icons.outlined.NotificationsActive
import androidx.compose.material.icons.outlined.Payments
import androidx.compose.material.icons.outlined.People
import androidx.compose.material.icons.outlined.Schedule
import androidx.compose.material.icons.outlined.Today
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.ViewWeek
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.insurance.mobile.R
import com.insurance.mobile.core.network.dto.UserDto
import com.insurance.mobile.core.util.InrCompactFormat
import com.insurance.mobile.feature.dashboard.data.DashboardOverview
import com.insurance.mobile.feature.dashboard.presentation.DashboardUiState
import com.insurance.mobile.feature.dashboard.presentation.DashboardViewModel
import com.insurance.mobile.feature.renewalwindow.domain.RenewalWindow
import com.insurance.mobile.ui.components.DashboardMetricTile
import com.insurance.mobile.ui.components.InsuranceFullScreenLoading
import com.insurance.mobile.ui.components.InsuranceTopBar
import com.insurance.mobile.ui.components.MetricCard
import com.insurance.mobile.ui.components.SectionCard
import com.insurance.mobile.ui.theme.LocalInsuranceExtendedColors
import java.text.NumberFormat
import java.util.Locale

/**
 * Home dashboard: pending payments highlight, expiring-soon metric, renewal summary. Read-only.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    user: UserDto,
    onOpenStatistics: () -> Unit,
    onOpenExpiring: () -> Unit,
    onOpenPolicies: () -> Unit,
    onOpenRenewalWindow: (RenewalWindow) -> Unit,
    onOpenServerSettings: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: DashboardViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) {
        viewModel.refresh()
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            InsuranceTopBar(
                title = stringResource(R.string.dashboard_title),
                actions = {
                    IconButton(onClick = onOpenServerSettings) {
                        Icon(
                            imageVector = Icons.Outlined.Settings,
                            contentDescription = stringResource(R.string.nav_server_settings),
                        )
                    }
                    androidx.compose.material3.TextButton(onClick = onOpenExpiring) {
                        Text(stringResource(R.string.nav_expiring))
                    }
                    androidx.compose.material3.TextButton(onClick = onOpenPolicies) {
                        Text(stringResource(R.string.nav_policies))
                    }
                    androidx.compose.material3.TextButton(onClick = onOpenStatistics) {
                        Text(stringResource(R.string.nav_statistics))
                    }
                },
            )
        },
    ) { padding ->
        when (val s = state) {
            DashboardUiState.Loading -> {
                InsuranceFullScreenLoading(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding),
                )
            }
            is DashboardUiState.Error -> {
                Column(
                    modifier = Modifier
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
            is DashboardUiState.Success -> {
                DashboardBody(
                    modifier = Modifier.padding(padding),
                    user = user,
                    overview = s.overview,
                    onOpenRenewalWindow = onOpenRenewalWindow,
                )
            }
        }
    }
}

@Composable
private fun DashboardHeader(
    displayName: String,
    email: String,
    asOfDate: String,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.large,
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.45f),
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Column(Modifier.padding(18.dp)) {
            Text(
                text = stringResource(R.string.dashboard_greeting, displayName),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onPrimaryContainer,
            )
            Text(
                text = email,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.85f),
                modifier = Modifier.padding(top = 4.dp),
            )
            Text(
                text = stringResource(R.string.dashboard_as_of, asOfDate),
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.75f),
                modifier = Modifier.padding(top = 10.dp),
            )
        }
    }
}

@Composable
private fun PendingPaymentsHighlightCard(
    policyCount: Int,
    pendingAmount: Double,
    modifier: Modifier = Modifier,
) {
    val extended = LocalInsuranceExtendedColors.current
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.large,
        colors = CardDefaults.cardColors(
            containerColor = extended.warningContainer.copy(alpha = 0.92f),
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp),
    ) {
        Row(
            Modifier.padding(18.dp),
            verticalAlignment = Alignment.Top,
            horizontalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Icon(
                imageVector = Icons.Outlined.Payments,
                contentDescription = null,
                modifier = Modifier.size(28.dp),
                tint = extended.onWarningContainer,
            )
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(
                    text = stringResource(R.string.dashboard_pending_title),
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = extended.onWarningContainer,
                )
                Text(
                    text = stringResource(R.string.dashboard_pending_policies_line, policyCount),
                    style = MaterialTheme.typography.bodyMedium,
                    color = extended.onWarningContainer.copy(alpha = 0.9f),
                )
                Text(
                    text = stringResource(
                        R.string.dashboard_pending_amount_line,
                        InrCompactFormat.format(pendingAmount),
                    ),
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold,
                    color = extended.onWarningContainer,
                )
            }
        }
    }
}

@Composable
private fun DashboardBody(
    modifier: Modifier = Modifier,
    user: UserDto,
    overview: DashboardOverview,
    onOpenRenewalWindow: (RenewalWindow) -> Unit,
) {
    val stats = overview.statistics
    val nf = NumberFormat.getNumberInstance(Locale.getDefault())
    val displayName = user.name?.takeIf { it.isNotBlank() } ?: user.email

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        DashboardHeader(
            displayName = displayName,
            email = user.email,
            asOfDate = stats.asOfDate,
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            DashboardMetricTile(
                title = stringResource(R.string.metric_total_customers),
                value = nf.format(stats.totalCustomers),
                icon = Icons.Outlined.People,
                modifier = Modifier.weight(1f),
            )
            DashboardMetricTile(
                title = stringResource(R.string.metric_total_policies),
                value = nf.format(stats.totalPolicies ?: 0),
                icon = Icons.Outlined.Description,
                modifier = Modifier.weight(1f),
            )
        }

        PendingPaymentsHighlightCard(
            policyCount = stats.pendingPaymentsCount,
            pendingAmount = stats.pendingPaymentsAmount,
        )

        MetricCard(
            title = stringResource(R.string.metric_expiring_soon),
            value = nf.format(overview.renewalSummary.expiringWithin365Days),
            subtitle = stringResource(R.string.metric_expiring_soon_subtitle),
            icon = Icons.Outlined.CalendarMonth,
            containerColor = MaterialTheme.colorScheme.tertiaryContainer.copy(alpha = 0.35f),
            iconTint = MaterialTheme.colorScheme.tertiary,
        )

        SectionCard(
            title = stringResource(R.string.section_renewal_reminders),
            icon = Icons.Outlined.NotificationsActive,
        ) {
            RenewalSummaryRows(overview, onOpenRenewalWindow)
        }

        Spacer(Modifier.height(16.dp))
    }
}

@Composable
private fun RenewalSummaryRows(
    overview: DashboardOverview,
    onOpenRenewalWindow: (RenewalWindow) -> Unit,
) {
    val s = overview.renewalSummary
    val nf = NumberFormat.getNumberInstance(Locale.getDefault())
    val today = s.expiringToday ?: 0

    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        RenewalSummaryClickableRow(
            label = stringResource(R.string.renewal_expiring_today),
            value = nf.format(today),
            icon = Icons.Outlined.Today,
            onClick = { onOpenRenewalWindow(RenewalWindow.TODAY) },
        )
        RenewalSummaryClickableRow(
            label = stringResource(R.string.renewal_expiring_7),
            value = nf.format(s.expiringWithin7Days),
            icon = Icons.Outlined.ViewWeek,
            onClick = { onOpenRenewalWindow(RenewalWindow.DAYS_7) },
        )
        RenewalSummaryClickableRow(
            label = stringResource(R.string.renewal_expiring_15),
            value = nf.format(s.expiringWithin15Days),
            icon = Icons.Outlined.Schedule,
            onClick = { onOpenRenewalWindow(RenewalWindow.DAYS_15) },
        )
        RenewalSummaryClickableRow(
            label = stringResource(R.string.renewal_expiring_30),
            value = nf.format(s.expiringWithin30Days),
            icon = Icons.Outlined.Event,
            onClick = { onOpenRenewalWindow(RenewalWindow.DAYS_30) },
        )
        RenewalSummaryClickableRow(
            label = stringResource(R.string.renewal_expired_active),
            value = nf.format(s.expired),
            icon = Icons.Outlined.ErrorOutline,
            onClick = { onOpenRenewalWindow(RenewalWindow.EXPIRED_ACTIVE) },
        )
    }
}

@Composable
private fun RenewalSummaryClickableRow(
    label: String,
    value: String,
    icon: ImageVector,
    onClick: () -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = MaterialTheme.shapes.medium,
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.65f),
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Row(
            Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                modifier = Modifier.size(22.dp),
                tint = MaterialTheme.colorScheme.primary,
            )
            Column(Modifier.weight(1f)) {
                Text(
                    text = label,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    text = value,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface,
                )
            }
        }
    }
}
