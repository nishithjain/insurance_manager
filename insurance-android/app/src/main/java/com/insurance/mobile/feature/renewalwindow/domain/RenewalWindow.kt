package com.insurance.mobile.feature.renewalwindow.domain

import androidx.annotation.StringRes
import com.insurance.mobile.R

/**
 * Dashboard renewal row → [routeArg] for [com.insurance.mobile.navigation.AppRoute.RenewalWindowList].
 */
enum class RenewalWindow(
    val routeArg: String,
    @StringRes val screenTitleRes: Int,
    @StringRes val emptyMessageRes: Int,
) {
    TODAY(
        routeArg = "today",
        screenTitleRes = R.string.renewal_window_screen_title_today,
        emptyMessageRes = R.string.renewal_window_empty_today,
    ),
    DAYS_7(
        routeArg = "7",
        screenTitleRes = R.string.renewal_window_screen_title_7,
        emptyMessageRes = R.string.renewal_window_empty_7,
    ),
    DAYS_15(
        routeArg = "15",
        screenTitleRes = R.string.renewal_window_screen_title_15,
        emptyMessageRes = R.string.renewal_window_empty_15,
    ),
    DAYS_30(
        routeArg = "30",
        screenTitleRes = R.string.renewal_window_screen_title_30,
        emptyMessageRes = R.string.renewal_window_empty_30,
    ),
    EXPIRED_ACTIVE(
        routeArg = "expired",
        screenTitleRes = R.string.renewal_window_screen_title_expired_active,
        emptyMessageRes = R.string.renewal_window_empty_expired_active,
    ),
    ;

    companion object {
        fun fromRouteArg(arg: String): RenewalWindow =
            entries.firstOrNull { it.routeArg == arg } ?: DAYS_7
    }
}
