package com.insurance.mobile.feature.expiring.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.insurance.mobile.R
import com.insurance.mobile.core.util.AppCurrency
import com.insurance.mobile.core.util.openWhatsAppWithFallback
import com.insurance.mobile.core.util.safeStartDialer
import com.insurance.mobile.core.util.sanitizePhoneNumber
import com.insurance.mobile.feature.expiring.domain.ExpiringPolicyItem
import com.insurance.mobile.ui.components.ContactActionButtonRow
import com.insurance.mobile.ui.components.ExpiryStatusBadge
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle

@Composable
fun ExpiringPolicyRow(
    item: ExpiringPolicyItem,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val currency = AppCurrency.formatter
    val expiryLabel = remember(item.endDateIso) {
        try {
            val d = LocalDate.parse(item.endDateIso)
            DateTimeFormatter.ofLocalizedDate(FormatStyle.MEDIUM).format(d)
        } catch (_: Exception) {
            item.endDateIso
        }
    }
    val sanitized = remember(item.customerPhone) { sanitizePhoneNumber(item.customerPhone) }
    val phoneDisplay = item.customerPhone.trim().takeUnless { it.isEmpty() }
        ?: stringResource(R.string.renewal_window_whatsapp_placeholder)

    Card(
        modifier = modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.large,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = item.customerName,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                    Text(
                        text = item.policyNumber,
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(top = 2.dp),
                    )
                }
                ExpiryStatusBadge(daysLeft = item.daysLeft)
            }

            Text(
                text = item.policyType,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.55f))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End,
            ) {
                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        text = stringResource(R.string.expiring_row_premium),
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        text = currency.format(item.premium),
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Medium,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = stringResource(R.string.expiring_row_company),
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        text = item.insurerCompany,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        text = stringResource(R.string.expiring_row_expiry),
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        text = expiryLabel,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            }

            if (sanitized != null) {
                Text(
                    text = "${stringResource(R.string.expiring_row_phone)}: $phoneDisplay",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.clickable {
                        safeStartDialer(context, sanitized)
                    },
                )
            } else {
                Text(
                    text = "${stringResource(R.string.expiring_row_phone)}: $phoneDisplay",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            if (sanitized != null) {
                ContactActionButtonRow(
                    callLabel = stringResource(R.string.renewal_window_action_call),
                    whatsAppLabel = stringResource(R.string.renewal_window_action_whatsapp),
                    onCall = { safeStartDialer(context, sanitized) },
                    onWhatsApp = {
                        val name = item.customerName.trim().takeUnless { it.isEmpty() }
                            ?: context.getString(R.string.renewal_window_whatsapp_name_fallback)
                        val type = item.policyType.trim().takeUnless { it.isEmpty() }
                            ?: context.getString(R.string.renewal_window_whatsapp_placeholder)
                        val message = context.getString(
                            R.string.renewal_window_whatsapp_message_template,
                            name,
                            type.lowercase(),
                            expiryLabel,
                        )
                        openWhatsAppWithFallback(context, sanitized, message)
                    },
                )
            }

            Text(
                text = "${stringResource(R.string.expiring_row_payment)}: ${item.paymentStatus}",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.outline,
            )
        }
    }
}
