package com.insurance.mobile.feature.statistics.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Analytics
import androidx.compose.material.icons.outlined.Assignment
import androidx.compose.material.icons.outlined.BarChart
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.EventRepeat
import androidx.compose.material.icons.outlined.People
import androidx.compose.material.icons.outlined.PieChart
import androidx.compose.material.icons.outlined.Repeat
import androidx.compose.material.icons.outlined.Savings
import androidx.compose.material.icons.outlined.TrendingUp
import androidx.compose.material.icons.outlined.WarningAmber
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.insurance.mobile.R
import com.insurance.mobile.core.network.dto.DashboardStatisticsDto
import com.insurance.mobile.core.util.AppCurrency
import com.insurance.mobile.feature.statistics.presentation.StatisticsUiState
import com.insurance.mobile.feature.statistics.presentation.StatisticsViewModel
import com.insurance.mobile.ui.components.InsuranceFullScreenLoading
import com.insurance.mobile.ui.components.InsuranceTopBar
import com.insurance.mobile.ui.components.MetricCard
import com.insurance.mobile.ui.components.SectionCard
import java.text.NumberFormat
import java.util.Locale

/**
 * Read-only statistics: same numbers as the web Statistics page + simple charts.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StatisticsScreen(
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: StatisticsViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) {
        viewModel.load()
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            InsuranceTopBar(
                title = stringResource(R.string.statistics_title),
                navigationIcon = {
                    androidx.compose.material3.TextButton(onClick = onBack) {
                        Text(stringResource(R.string.action_back))
                    }
                },
            )
        },
    ) { padding ->
        when (val s = state) {
            StatisticsUiState.Loading -> {
                InsuranceFullScreenLoading(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding),
                )
            }
            is StatisticsUiState.Error -> {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding)
                        .padding(24.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    Text(text = s.message, color = MaterialTheme.colorScheme.error)
                    Button(onClick = { viewModel.load() }) {
                        Text(stringResource(R.string.action_retry))
                    }
                }
            }
            is StatisticsUiState.Success -> {
                StatisticsBody(
                    modifier = Modifier.padding(padding),
                    data = s.data,
                )
            }
        }
    }
}

@Composable
private fun StatisticsBody(
    modifier: Modifier = Modifier,
    data: DashboardStatisticsDto,
) {
    val nf = NumberFormat.getNumberInstance(Locale.getDefault())
    val currency = AppCurrency.formatter
    val pct = NumberFormat.getPercentInstance(Locale.getDefault()).apply {
        minimumFractionDigits = 1
        maximumFractionDigits = 1
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text(
            text = stringResource(R.string.statistics_as_of, data.asOfDate, data.currentMonthLabel),
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        SectionCard(
            title = stringResource(R.string.stat_section_overview),
            icon = Icons.Outlined.Analytics,
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                MetricCard(
                    title = stringResource(R.string.metric_total_customers),
                    value = nf.format(data.totalCustomers),
                    icon = Icons.Outlined.People,
                )
                MetricCard(
                    title = stringResource(R.string.metric_total_policies),
                    value = nf.format(data.totalPolicies ?: 0),
                    icon = Icons.Outlined.Description,
                )
            }
        }

        MetricCard(
            title = stringResource(R.string.stat_metric_payments_month),
            value = currency.format(data.paymentReceivedThisMonth),
            icon = Icons.Outlined.Savings,
            containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f),
        )
        MetricCard(
            title = stringResource(R.string.stat_metric_pending),
            value = nf.format(data.pendingPaymentsCount),
            subtitle = stringResource(
                R.string.stat_metric_pending_sub,
                currency.format(data.pendingPaymentsAmount),
            ),
            icon = Icons.Outlined.WarningAmber,
            iconTint = MaterialTheme.colorScheme.tertiary,
            containerColor = MaterialTheme.colorScheme.tertiaryContainer.copy(alpha = 0.35f),
        )
        MetricCard(
            title = stringResource(R.string.stat_metric_renewals_month),
            value = nf.format(data.renewalsThisMonth),
            icon = Icons.Outlined.EventRepeat,
        )
        MetricCard(
            title = stringResource(R.string.stat_metric_expiring_month),
            value = nf.format(data.expiringThisMonth),
            icon = Icons.Outlined.Assignment,
        )
        MetricCard(
            title = stringResource(R.string.stat_metric_conversion),
            value = data.renewalConversionRate?.let { pct.format(it) }
                ?: stringResource(R.string.stat_metric_na),
            subtitle = stringResource(R.string.stat_metric_conversion_sub),
            icon = Icons.Outlined.TrendingUp,
        )
        MetricCard(
            title = stringResource(R.string.stat_metric_expired_open),
            value = nf.format(data.expiredNotRenewedOpen),
            icon = Icons.Outlined.WarningAmber,
        )
        MetricCard(
            title = stringResource(R.string.stat_metric_repeat_customers),
            value = nf.format(data.repeatCustomers),
            subtitle = stringResource(R.string.stat_metric_repeat_sub, nf.format(data.totalCustomers)),
            icon = Icons.Outlined.Repeat,
        )

        SectionCard(
            title = stringResource(R.string.stat_section_trend),
            icon = Icons.Outlined.BarChart,
        ) {
            MonthlyTrendChart(rows = data.monthlyTrend)
        }

        SectionCard(
            title = stringResource(R.string.stat_section_policy_types),
            icon = Icons.Outlined.PieChart,
        ) {
            PolicyTypeDistributionChart(items = data.policyTypeDistribution)
        }

        Spacer(Modifier.height(24.dp))
    }
}
