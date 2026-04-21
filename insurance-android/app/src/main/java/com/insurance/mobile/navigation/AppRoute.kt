package com.insurance.mobile.navigation

/**
 * Main graph destinations after login.
 */
object AppRoute {
    const val Dashboard = "main/dashboard"
    const val Statistics = "main/statistics"
    const val Expiring = "main/expiring"
    const val PoliciesList = "main/policies"
    const val PolicyDetail = "main/policy/{policyId}"
    const val RenewalWindowList = "main/renewal-window/{window}"

    fun policyDetailRoute(policyId: String) = "main/policy/$policyId"

    fun renewalWindowListRoute(window: String) = "main/renewal-window/$window"
}
