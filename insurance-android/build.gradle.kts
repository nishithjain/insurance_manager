/**
 * Top-level Gradle file: declares plugin versions used across modules.
 * Module-specific configuration lives in app/build.gradle.kts.
 */
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.android) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.hilt) apply false
    alias(libs.plugins.ksp) apply false // Hilt code generation (replaces kapt for Hilt)
}
