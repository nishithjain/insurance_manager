package com.insurance.mobile.feature.statistics.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.insurance.mobile.core.network.dto.MonthlyTrendDto
import com.insurance.mobile.core.network.dto.PolicyTypeCountDto
import kotlin.math.max

private const val BarMaxDp = 96

/**
 * Simple grouped vertical bars per month (read-only).
 */
@Composable
fun MonthlyTrendChart(
    rows: List<MonthlyTrendDto>,
    modifier: Modifier = Modifier,
) {
    if (rows.isEmpty()) {
        ChartEmptyPlaceholder("No trend data for this period.")
        return
    }
    val maxVal = rows.maxOf { r ->
        max(max(r.paymentsReceived, r.renewals.toDouble()), r.expiring.toDouble())
    }.coerceAtLeast(1.0)

    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.medium,
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f),
    ) {
        Column(
            Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            rows.forEach { row ->
                Text(
                    text = row.month,
                    style = MaterialTheme.typography.titleSmall,
                    color = MaterialTheme.colorScheme.onSurface,
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.Bottom,
                ) {
                    VerticalMetricBar(
                        value = row.paymentsReceived,
                        max = maxVal,
                        color = MaterialTheme.colorScheme.primary,
                        label = "Pay",
                    )
                    VerticalMetricBar(
                        value = row.renewals.toDouble(),
                        max = maxVal,
                        color = MaterialTheme.colorScheme.secondary,
                        label = "Ren",
                    )
                    VerticalMetricBar(
                        value = row.expiring.toDouble(),
                        max = maxVal,
                        color = MaterialTheme.colorScheme.tertiary,
                        label = "Exp",
                    )
                }
            }
            LegendRow()
        }
    }
}

@Composable
private fun ChartEmptyPlaceholder(message: String) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.medium,
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f),
    ) {
        Text(
            text = message,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(20.dp),
        )
    }
}

@Composable
private fun RowScope.VerticalMetricBar(
    value: Double,
    max: Double,
    color: Color,
    label: String,
) {
    val fraction = if (max > 0) (value / max).toFloat().coerceIn(0f, 1f) else 0f
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier.weight(1f),
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(BarMaxDp.dp),
            contentAlignment = Alignment.BottomCenter,
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth(0.7f)
                    .height((BarMaxDp * fraction).dp)
                    .clip(RoundedCornerShape(topStart = 8.dp, topEnd = 8.dp))
                    .background(color),
            )
        }
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(top = 6.dp),
        )
    }
}

@Composable
private fun LegendRow() {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 4.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        LegendItem(color = MaterialTheme.colorScheme.primary, text = "Payments received")
        LegendItem(color = MaterialTheme.colorScheme.secondary, text = "Renewals resolved")
        LegendItem(color = MaterialTheme.colorScheme.tertiary, text = "Policies expiring (month)")
    }
}

@Composable
private fun LegendItem(color: Color, text: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Spacer(
            modifier = Modifier
                .width(12.dp)
                .height(12.dp)
                .clip(RoundedCornerShape(3.dp))
                .background(color),
        )
        Text(
            text = text,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(start = 8.dp),
        )
    }
}

/**
 * Horizontal bars for policy type counts (read-only).
 */
@Composable
fun PolicyTypeDistributionChart(
    items: List<PolicyTypeCountDto>,
    modifier: Modifier = Modifier,
) {
    if (items.isEmpty()) {
        ChartEmptyPlaceholder("No policy type breakdown yet.")
        return
    }
    val maxCount = items.maxOf { it.count }.coerceAtLeast(1)
    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        items.forEach { item ->
            val frac = item.count.toFloat() / maxCount
            Text(
                text = item.policyType,
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.onSurface,
            )
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(26.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.55f)),
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxHeight()
                        .fillMaxWidth(frac.coerceIn(0.08f, 1f))
                        .align(Alignment.CenterStart)
                        .clip(RoundedCornerShape(8.dp))
                        .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.88f)),
                )
            }
            Text(
                text = "${item.count} policies",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
