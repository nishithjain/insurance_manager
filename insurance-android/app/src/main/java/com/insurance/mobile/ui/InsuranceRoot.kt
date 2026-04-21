package com.insurance.mobile.ui

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.insurance.mobile.core.network.dto.UserDto
import com.insurance.mobile.feature.settings.ServerSetupScreen
import com.insurance.mobile.feature.startup.StartupScreen
import com.insurance.mobile.navigation.RootRoute
import com.insurance.mobile.ui.navigation.MainShell

/** Single-tenant app: no sign-in; API uses a default user on the server. */
private val localDisplayUser = UserDto(
    userId = "user_dev_local",
    email = "dev@local.insurance",
    name = "Local",
    picture = null,
    createdAt = "1970-01-01T00:00:00+00:00",
)

@Composable
fun InsuranceRoot() {
    val navController = rememberNavController()
    Surface(color = MaterialTheme.colorScheme.background) {
        NavHost(
            navController = navController,
            startDestination = RootRoute.Startup,
            modifier = Modifier.fillMaxSize(),
        ) {
            composable(RootRoute.Startup) {
                StartupScreen(
                    onNavigateToMain = {
                        navController.navigate(RootRoute.Main) {
                            popUpTo(RootRoute.Startup) { inclusive = true }
                        }
                    },
                    onNavigateToServerSetup = {
                        navController.navigate(RootRoute.ServerSetup) {
                            popUpTo(RootRoute.Startup) { inclusive = true }
                        }
                    },
                )
            }
            composable(RootRoute.ServerSetup) {
                val canGoBack = navController.previousBackStackEntry != null
                ServerSetupScreen(
                    showBack = canGoBack,
                    onBack = { navController.popBackStack() },
                    onSaveSuccess = {
                        if (canGoBack) {
                            navController.popBackStack()
                        } else {
                            navController.navigate(RootRoute.Main) {
                                popUpTo(RootRoute.ServerSetup) { inclusive = true }
                            }
                        }
                    },
                )
            }
            composable(RootRoute.Main) {
                MainShell(
                    user = localDisplayUser,
                    onOpenServerSettings = {
                        navController.navigate(RootRoute.ServerSetup)
                    },
                )
            }
        }
    }
}
