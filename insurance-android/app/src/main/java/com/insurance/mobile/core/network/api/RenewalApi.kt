package com.insurance.mobile.core.network.api

import com.insurance.mobile.core.network.dto.ExpiringWindowPolicyDto
import com.insurance.mobile.core.network.dto.RenewalRemindersDto
import retrofit2.http.GET
import retrofit2.http.Query

/**
 * Expiring-policy buckets + summary counts + window list (same rules as summary).
 */
interface RenewalApi {

    @GET("renewals/reminders")
    suspend fun getRenewalReminders(): RenewalRemindersDto

    /** [window] is `today`, `7`, `15`, `30`, or `expired` — same rules as the dashboard renewal summary. */
    @GET("renewals/expiring-list")
    suspend fun getExpiringList(@Query("window") window: String): List<ExpiringWindowPolicyDto>
}
