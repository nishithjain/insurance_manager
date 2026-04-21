package com.insurance.mobile.ui.navigation

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.insurance.mobile.core.network.dto.UserDto
import com.insurance.mobile.feature.dashboard.ui.DashboardScreen
import com.insurance.mobile.feature.expiring.ui.ExpiringPoliciesScreen
import com.insurance.mobile.feature.renewalwindow.ui.RenewalWindowListScreen
import com.insurance.mobile.feature.policies.ui.PoliciesListScreen
import com.insurance.mobile.feature.policies.ui.PolicyDetailScreen
import com.insurance.mobile.feature.statistics.ui.StatisticsScreen
import com.insurance.mobile.navigation.AppRoute

/**
 * Root navigation: Dashboard, Statistics, policies (read-only).
 */
@Composable
fun MainShell(
    user: UserDto,
    onOpenServerSettings: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val navController = rememberNavController()

    NavHost(
        navController = navController,
        startDestination = AppRoute.Dashboard,
        modifier = modifier.fillMaxSize(),
    ) {
        composable(AppRoute.Dashboard) {
            DashboardScreen(
                user = user,
                onOpenStatistics = {
                    navController.navigate(AppRoute.Statistics)
                },
                onOpenExpiring = {
                    navController.navigate(AppRoute.Expiring)
                },
                onOpenPolicies = {
                    navController.navigate(AppRoute.PoliciesList)
                },
                onOpenRenewalWindow = { w ->
                    navController.navigate(AppRoute.renewalWindowListRoute(w.routeArg))
                },
                onOpenServerSettings = onOpenServerSettings,
            )
        }
        composable(
            route = AppRoute.RenewalWindowList,
            arguments = listOf(
                navArgument("window") { type = NavType.StringType },
            ),
        ) {
            RenewalWindowListScreen(
                onBack = { navController.popBackStack() },
                onPolicyClick = { policyId ->
                    navController.navigate(AppRoute.policyDetailRoute(policyId))
                },
            )
        }
        composable(AppRoute.Statistics) {
            StatisticsScreen(
                onBack = { navController.popBackStack() },
            )
        }
        composable(AppRoute.Expiring) {
            ExpiringPoliciesScreen(
                onBack = { navController.popBackStack() },
            )
        }
        composable(AppRoute.PoliciesList) {
            PoliciesListScreen(
                onBack = { navController.popBackStack() },
                onPolicyClick = { policyId ->
                    navController.navigate(AppRoute.policyDetailRoute(policyId))
                },
            )
        }
        composable(
            route = AppRoute.PolicyDetail,
            arguments = listOf(
                navArgument("policyId") { type = NavType.StringType },
            ),
        ) {
            PolicyDetailScreen(
                onBack = { navController.popBackStack() },
            )
        }
    }
}
