package com.insurance.mobile.ui

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.insurance.mobile.core.auth.AuthSession
import com.insurance.mobile.core.network.dto.UserDto
import com.insurance.mobile.feature.login.LoginScreen
import com.insurance.mobile.feature.settings.ServerSetupScreen
import com.insurance.mobile.feature.startup.StartupScreen
import com.insurance.mobile.navigation.RootRoute
import com.insurance.mobile.ui.navigation.MainShell

/**
 * Root graph. Also hosts the global 401/403 listener so any expired session
 * bounces the user back to the login screen from anywhere in the app.
 */
@Composable
fun InsuranceRoot(rootViewModel: RootViewModel = hiltViewModel()) {
    val navController = rememberNavController()
    val session by rootViewModel.session.collectAsState()

    LaunchedEffect(Unit) {
        rootViewModel.unauthorizedEvents.collect {
            navController.navigate(RootRoute.Login) {
                popUpTo(RootRoute.Startup) { inclusive = true }
                launchSingleTop = true
            }
        }
    }

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
                    onNavigateToLogin = {
                        navController.navigate(RootRoute.Login) {
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
                            navController.navigate(RootRoute.Login) {
                                popUpTo(RootRoute.ServerSetup) { inclusive = true }
                            }
                        }
                    },
                )
            }
            composable(RootRoute.Login) {
                LoginScreen(
                    onSignedIn = {
                        navController.navigate(RootRoute.Main) {
                            popUpTo(RootRoute.Login) { inclusive = true }
                        }
                    },
                    onOpenServerSettings = {
                        navController.navigate(RootRoute.ServerSetup)
                    },
                )
            }
            composable(RootRoute.Main) {
                MainShell(
                    user = session?.let(::toUserDto) ?: UNKNOWN_USER,
                    onOpenServerSettings = {
                        navController.navigate(RootRoute.ServerSetup)
                    },
                )
            }
        }
    }
}

/** Placeholder shown only in the unlikely case Main is hit before hydration. */
private val UNKNOWN_USER = UserDto(
    userId = "unknown",
    email = "",
    name = "",
    picture = null,
    createdAt = "1970-01-01T00:00:00+00:00",
)

/**
 * Adapt the auth session to the legacy [UserDto] expected by the main shell.
 * This keeps the existing screens untouched — they still receive a
 * display-only user object, just sourced from real identity now.
 */
private fun toUserDto(session: AuthSession): UserDto = UserDto(
    userId = session.userId.toString(),
    email = session.email,
    name = session.fullName.ifBlank { session.email },
    picture = null,
    createdAt = "1970-01-01T00:00:00+00:00",
)
