package com.insurance.mobile.feature.startup

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import com.insurance.mobile.ui.components.InsuranceFullScreenLoading

/**
 * Splash: loads saved URL, checks health, then navigates to main or server setup.
 */
@Composable
fun StartupScreen(
    onNavigateToMain: () -> Unit,
    onNavigateToServerSetup: () -> Unit,
    onNavigateToLogin: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: StartupViewModel = hiltViewModel(),
) {
    LaunchedEffect(Unit) {
        when (viewModel.resolveDestination()) {
            StartupDestination.Main -> onNavigateToMain()
            StartupDestination.ServerSetup -> onNavigateToServerSetup()
            StartupDestination.Login -> onNavigateToLogin()
        }
    }

    InsuranceFullScreenLoading(modifier = modifier.fillMaxSize())
}
