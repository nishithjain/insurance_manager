package com.insurance.mobile.feature.policies.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.insurance.mobile.R
import com.insurance.mobile.core.network.dto.HealthPolicyDetailsDto
import com.insurance.mobile.core.network.dto.MotorPolicyDetailsDto
import com.insurance.mobile.core.network.dto.PolicyDetailResponseDto
import com.insurance.mobile.core.network.dto.PropertyPolicyDetailsDto
import com.insurance.mobile.feature.policies.presentation.PolicyDetailUiState
import com.insurance.mobile.feature.policies.presentation.PolicyDetailViewModel
import com.insurance.mobile.core.util.AppCurrency
import com.insurance.mobile.ui.components.InsuranceFullScreenLoading
import com.insurance.mobile.ui.components.InsuranceTopBar
import com.insurance.mobile.ui.components.SectionCard
import java.text.NumberFormat
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle

/**
 * Read-only policy detail: customer, policy, payment, renewal/contact, line-of-business extras.
 *
 * **API:** `GET /policies/{id}/detail` → [PolicyDetailResponseDto].
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PolicyDetailScreen(
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: PolicyDetailViewModel = hiltViewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            InsuranceTopBar(
                title = stringResource(R.string.policy_detail_title),
                navigationIcon = {
                    androidx.compose.material3.TextButton(onClick = onBack) {
                        Text(stringResource(R.string.action_back))
                    }
                },
                actions = {
                    androidx.compose.material3.TextButton(onClick = { viewModel.load() }) {
                        Text(stringResource(R.string.action_refresh))
                    }
                },
            )
        },
    ) { padding ->
        when (val s = uiState) {
            PolicyDetailUiState.Loading -> {
                InsuranceFullScreenLoading(
                    Modifier
                        .fillMaxSize()
                        .padding(padding),
                )
            }
            is PolicyDetailUiState.Error -> {
                Column(
                    Modifier
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
            is PolicyDetailUiState.Success -> {
                PolicyDetailBody(
                    modifier = Modifier.padding(padding),
                    detail = s.detail,
                )
            }
        }
    }
}

@Composable
private fun PolicyDetailBody(
    detail: PolicyDetailResponseDto,
    modifier: Modifier = Modifier,
) {
    val currency = AppCurrency.formatter
    val p = detail.policy
    val c = detail.customer

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text(
            text = p.policyNumber,
            style = MaterialTheme.typography.headlineSmall,
        )
        Text(
            text = stringResource(R.string.policy_detail_category, detail.categoryGroup),
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.secondary,
        )

        SectionCard(title = stringResource(R.string.policy_section_customer)) {
            DetailLine(stringResource(R.string.detail_label_name), c.name)
            DetailLine(stringResource(R.string.detail_label_email), c.email)
            DetailLine(stringResource(R.string.detail_label_phone), c.phone)
            DetailLine(stringResource(R.string.detail_label_address), c.address)
        }

        SectionCard(title = stringResource(R.string.policy_section_policy)) {
            DetailLine(stringResource(R.string.detail_label_policy_type), p.policyType)
            DetailLine(stringResource(R.string.detail_label_insurer), p.insurerCompany)
            DetailLine(stringResource(R.string.detail_label_premium), currency.format(p.premium))
            DetailLine(stringResource(R.string.detail_label_start_date), formatIsoDate(p.startDate))
            DetailLine(stringResource(R.string.detail_label_end_date), formatIsoDate(p.endDate))
            DetailLine(stringResource(R.string.detail_label_status), p.status)
        }

        SectionCard(title = stringResource(R.string.policy_section_payment)) {
            DetailLine(stringResource(R.string.detail_label_payment_status), p.paymentStatus)
            DetailLine(stringResource(R.string.detail_label_payment_note), p.paymentNote)
            DetailLine(
                stringResource(R.string.detail_label_payment_updated),
                formatIsoDateTime(p.paymentUpdatedAt),
            )
        }

        SectionCard(title = stringResource(R.string.policy_section_renewal_contact)) {
            DetailLine(stringResource(R.string.detail_label_contact_status), p.contactStatus)
            DetailLine(
                stringResource(R.string.detail_label_last_contacted),
                formatIsoDateTime(p.lastContactedAt),
            )
            DetailLine(stringResource(R.string.detail_label_follow_up), formatIsoDate(p.followUpDate))
            DetailLine(stringResource(R.string.detail_label_renewal_status), p.renewalStatus)
            DetailLine(
                stringResource(R.string.detail_label_renewal_note),
                p.renewalResolutionNote,
            )
            DetailLine(
                stringResource(R.string.detail_label_renewal_resolved_at),
                formatIsoDateTime(p.renewalResolvedAt),
            )
            DetailLine(
                stringResource(R.string.detail_label_renewal_resolved_by),
                p.renewalResolvedBy,
            )
        }

        detail.motor?.let { motor ->
            SectionCard(title = stringResource(R.string.policy_section_motor)) {
                MotorBlock(motor, currency)
            }
        }
        detail.health?.let { health ->
            SectionCard(title = stringResource(R.string.policy_section_health)) {
                HealthBlock(health, currency)
            }
        }
        detail.propertyDetail?.let { prop ->
            SectionCard(title = stringResource(R.string.policy_section_property)) {
                PropertyBlock(prop, currency)
            }
        }
    }
}

@Composable
private fun MotorBlock(
    m: MotorPolicyDetailsDto,
    currency: NumberFormat,
) {
    DetailLine(stringResource(R.string.detail_motor_vehicle_no), m.vehicleNo)
    DetailLine(stringResource(R.string.detail_motor_vehicle_details), m.vehicleDetails)
    m.idvOfVehicle?.let {
        DetailLine(stringResource(R.string.detail_motor_idv), currency.format(it))
    }
    DetailLine(stringResource(R.string.detail_motor_engine), m.engineNo)
    DetailLine(stringResource(R.string.detail_motor_chassis), m.chassisNo)
    m.odPremium?.let {
        DetailLine(stringResource(R.string.detail_motor_od_premium), currency.format(it))
    }
    m.tpPremium?.let {
        DetailLine(stringResource(R.string.detail_motor_tp_premium), currency.format(it))
    }
}

@Composable
private fun HealthBlock(
    h: HealthPolicyDetailsDto,
    currency: NumberFormat,
) {
    DetailLine(stringResource(R.string.detail_health_plan), h.planName)
    h.sumInsured?.let {
        DetailLine(stringResource(R.string.detail_health_sum_insured), currency.format(it))
    }
    DetailLine(stringResource(R.string.detail_health_cover), h.coverType)
    DetailLine(stringResource(R.string.detail_health_members), h.membersCovered)
    h.basePremium?.let {
        DetailLine(stringResource(R.string.detail_health_base_premium), currency.format(it))
    }
    h.additionalPremium?.let {
        DetailLine(stringResource(R.string.detail_health_additional_premium), currency.format(it))
    }
}

@Composable
private fun PropertyBlock(
    p: PropertyPolicyDetailsDto,
    currency: NumberFormat,
) {
    DetailLine(stringResource(R.string.detail_property_product), p.productName)
    p.sumInsured?.let {
        DetailLine(stringResource(R.string.detail_property_sum_insured), currency.format(it))
    }
    DetailLine(stringResource(R.string.detail_property_sub_product), p.subProduct)
    DetailLine(stringResource(R.string.detail_property_risk_location), p.riskLocation)
    p.basePremium?.let {
        DetailLine(stringResource(R.string.detail_property_base_premium), currency.format(it))
    }
    p.additionalPremium?.let {
        DetailLine(stringResource(R.string.detail_property_additional_premium), currency.format(it))
    }
}

@Composable
private fun DetailLine(
    label: String,
    value: String?,
) {
    val dash = stringResource(R.string.stat_metric_na)
    val display = value?.takeIf { it.isNotBlank() } ?: dash
    Column(Modifier.padding(vertical = 4.dp)) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(text = display, style = MaterialTheme.typography.bodyLarge)
    }
}

private fun formatIsoDate(iso: String?): String? {
    if (iso.isNullOrBlank()) return null
    return try {
        val d = LocalDate.parse(iso.take(10))
        DateTimeFormatter.ofLocalizedDate(FormatStyle.MEDIUM).format(d)
    } catch (_: Exception) {
        iso
    }
}

private fun formatIsoDateTime(iso: String?): String? {
    if (iso.isNullOrBlank()) return null
    return try {
        if (iso.length >= 10) {
            val d = LocalDate.parse(iso.take(10))
            DateTimeFormatter.ofLocalizedDate(FormatStyle.MEDIUM).format(d)
        } else iso
    } catch (_: Exception) {
        iso
    }
}
