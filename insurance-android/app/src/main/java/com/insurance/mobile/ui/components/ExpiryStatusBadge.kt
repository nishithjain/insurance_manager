package com.insurance.mobile.ui.components

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.insurance.mobile.R
import com.insurance.mobile.ui.theme.LocalInsuranceExtendedColors

/**
 * Days-until-expiry or overdue chip for policy rows. [daysLeft] negative means overdue.
 */
@Composable
fun ExpiryStatusBadge(
    daysLeft: Int,
    modifier: Modifier = Modifier,
) {
    val extended = LocalInsuranceExtendedColors.current
    val (label, bg, fg) = when {
        daysLeft > 7 -> Triple(
            stringResource(R.string.renewal_window_days_badge, daysLeft),
            MaterialTheme.colorScheme.secondaryContainer,
            MaterialTheme.colorScheme.onSecondaryContainer,
        )
        daysLeft > 0 -> Triple(
            stringResource(R.string.renewal_window_days_badge, daysLeft),
            MaterialTheme.colorScheme.tertiaryContainer,
            MaterialTheme.colorScheme.onTertiaryContainer,
        )
        daysLeft == 0 -> Triple(
            stringResource(R.string.renewal_window_days_badge_today),
            extended.warningContainer,
            extended.onWarningContainer,
        )
        else -> Triple(
            stringResource(R.string.renewal_window_days_badge_overdue, -daysLeft),
            MaterialTheme.colorScheme.errorContainer,
            MaterialTheme.colorScheme.onErrorContainer,
        )
    }
    StatusChip(text = label, containerColor = bg, contentColor = fg, modifier = modifier)
}

@Composable
fun StatusChip(
    text: String,
    containerColor: Color,
    contentColor: Color,
    modifier: Modifier = Modifier,
) {
    Surface(
        modifier = modifier,
        shape = MaterialTheme.shapes.small,
        color = containerColor,
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.labelLarge,
            color = contentColor,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
        )
    }
}
