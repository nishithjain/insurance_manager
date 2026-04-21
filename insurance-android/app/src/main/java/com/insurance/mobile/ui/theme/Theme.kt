package com.insurance.mobile.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

/**
 * Extra semantic colors for warnings (pending payments, urgent expiry) not in [androidx.compose.material3.ColorScheme].
 */
data class InsuranceExtendedColors(
    val warning: Color = Warning,
    val warningContainer: Color = WarningContainer,
    val onWarningContainer: Color = OnWarningContainer,
)

val LocalInsuranceExtendedColors = staticCompositionLocalOf { InsuranceExtendedColors() }

private val LightColors = lightColorScheme(
    primary = Primary,
    onPrimary = OnPrimary,
    primaryContainer = PrimaryContainer,
    onPrimaryContainer = OnPrimaryContainer,
    secondary = Secondary,
    onSecondary = OnSecondary,
    secondaryContainer = SecondaryContainer,
    onSecondaryContainer = OnSecondaryContainer,
    tertiary = Tertiary,
    onTertiary = OnTertiary,
    tertiaryContainer = TertiaryContainer,
    onTertiaryContainer = OnTertiaryContainer,
    error = Error,
    onError = OnError,
    errorContainer = ErrorContainer,
    onErrorContainer = OnErrorContainer,
    background = Background,
    onBackground = OnBackground,
    surface = Surface,
    onSurface = OnSurface,
    surfaceVariant = SurfaceVariant,
    onSurfaceVariant = OnSurfaceVariant,
    outline = Outline,
    outlineVariant = OutlineVariant,
)

@Composable
fun InsuranceTheme(content: @Composable () -> Unit) {
    CompositionLocalProvider(
        LocalInsuranceExtendedColors provides InsuranceExtendedColors(),
    ) {
        MaterialTheme(
            colorScheme = LightColors,
            typography = InsuranceTypography,
            shapes = InsuranceShapes,
            content = content,
        )
    }
}
