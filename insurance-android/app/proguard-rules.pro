# --- Retrofit / OkHttp ---
-dontwarn okhttp3.**
-dontwarn retrofit2.**

# --- Moshi (if you later enable codegen / reflect) ---
-keep class com.squareup.moshi.** { *; }
-keepclassmembers class * {
    @com.squareup.moshi.Json *;
}

# --- Data classes used as JSON (adjust package if you rename) ---
-keep class com.insurance.mobile.core.network.dto.** { *; }
-dontwarn androidx.compose.material3.pulltorefresh.**
