package com.insurance.mobile.core.network.dto

import com.squareup.moshi.Json

/**
 * Response from `GET /policies/{id}/detail` (see backend [PolicyDetailBundle]).
 */
data class PolicyDetailResponseDto(
    val policy: PolicyDto,
    val customer: CustomerDto,
    @Json(name = "category_group") val categoryGroup: String,
    val motor: MotorPolicyDetailsDto? = null,
    val health: HealthPolicyDetailsDto? = null,
    @Json(name = "property_detail") val propertyDetail: PropertyPolicyDetailsDto? = null,
)

data class MotorPolicyDetailsDto(
    @Json(name = "vehicle_no") val vehicleNo: String? = null,
    @Json(name = "vehicle_details") val vehicleDetails: String? = null,
    @Json(name = "idv_of_vehicle") val idvOfVehicle: Double? = null,
    @Json(name = "engine_no") val engineNo: String? = null,
    @Json(name = "chassis_no") val chassisNo: String? = null,
    @Json(name = "od_premium") val odPremium: Double? = null,
    @Json(name = "tp_premium") val tpPremium: Double? = null,
)

data class HealthPolicyDetailsDto(
    @Json(name = "plan_name") val planName: String? = null,
    @Json(name = "sum_insured") val sumInsured: Double? = null,
    @Json(name = "cover_type") val coverType: String? = null,
    @Json(name = "members_covered") val membersCovered: String? = null,
    @Json(name = "base_premium") val basePremium: Double? = null,
    @Json(name = "additional_premium") val additionalPremium: Double? = null,
)

data class PropertyPolicyDetailsDto(
    @Json(name = "product_name") val productName: String? = null,
    @Json(name = "sum_insured") val sumInsured: Double? = null,
    @Json(name = "sub_product") val subProduct: String? = null,
    @Json(name = "risk_location") val riskLocation: String? = null,
    @Json(name = "base_premium") val basePremium: Double? = null,
    @Json(name = "additional_premium") val additionalPremium: Double? = null,
)
