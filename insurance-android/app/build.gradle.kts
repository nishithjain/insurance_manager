/**
 * App module: dependencies, Compose, Hilt, Retrofit.
 *
 * Real API base URL is configured in-app (Server Setup). [BuildConfig.PLACEHOLDER_API_BASE_URL]
 * is only for Retrofit; requests are rewritten to the user-configured host.
 */

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.hilt)
    alias(libs.plugins.ksp)
}

android {
    namespace = "com.insurance.mobile"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.insurance.mobile"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"

        // Dummy host for Retrofit; [DynamicHostInterceptor] replaces scheme/host/port per saved URL.
        buildConfigField(
            "String",
            "PLACEHOLDER_API_BASE_URL",
            "\"http://127.0.0.1/api/\"",
        )

        // Google Sign-In Web Client ID. Must match the backend's GOOGLE_CLIENT_ID.
        // Override per build via gradle.properties: GOOGLE_WEB_CLIENT_ID=...
        val googleWebClientId: String =
            (project.findProperty("GOOGLE_WEB_CLIENT_ID") as String?) ?: ""
        buildConfigField(
            "String",
            "GOOGLE_WEB_CLIENT_ID",
            "\"$googleWebClientId\"",
        )
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
            buildConfigField(
                "String",
                "PLACEHOLDER_API_BASE_URL",
                "\"http://127.0.0.1/api/\"",
            )
            val googleWebClientId: String =
                (project.findProperty("GOOGLE_WEB_CLIENT_ID") as String?) ?: ""
            buildConfigField(
                "String",
                "GOOGLE_WEB_CLIENT_ID",
                "\"$googleWebClientId\"",
            )
        }
        debug {
            // Cleartext allowed via debug/AndroidManifest.xml (local HTTP)
            isDebuggable = true
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

composeCompiler {
    // Explicit options avoid some IDE/Gradle integrations passing null compose plugin flags.
    enableStrongSkippingMode = true
}

// hilt {
//     enableAggregatingTask = true
// }

/*
ksp {
    arg("hilt.enableAggregatingTask", "true")
}
*/

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation("androidx.compose.material:material-icons-extended")
    debugImplementation(libs.androidx.compose.ui.tooling)

    implementation(libs.androidx.navigation.compose)

    implementation(libs.kotlinx.coroutines.android)

    implementation(libs.hilt.android)
    ksp(libs.hilt.android.compiler)
    implementation(libs.hilt.navigation.compose)

    implementation(libs.retrofit)
    implementation(libs.retrofit.converter.moshi)
    implementation(libs.okhttp)
    implementation(libs.okhttp.logging)
    implementation(libs.moshi)
    implementation(libs.moshi.kotlin)

    implementation(libs.androidx.datastore.preferences)

    // Google Sign-In via the modern Credential Manager API.
    implementation(libs.androidx.credentials)
    implementation(libs.androidx.credentials.play.services.auth)
    implementation(libs.googleid)
}
