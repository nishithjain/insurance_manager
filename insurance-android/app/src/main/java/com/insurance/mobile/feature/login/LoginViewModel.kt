package com.insurance.mobile.feature.login

// --- Google Sign-In imports (disabled for emulator/dev) ---
// Uncomment along with signInWithGoogle() below to re-enable Google auth.
// import android.content.Context
// import androidx.credentials.CredentialManager
// import androidx.credentials.CustomCredential
// import androidx.credentials.GetCredentialRequest
// import androidx.credentials.exceptions.GetCredentialCancellationException
// import androidx.credentials.exceptions.GetCredentialException
// import com.google.android.libraries.identity.googleid.GetGoogleIdOption
// import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
// import com.insurance.mobile.BuildConfig
// import com.insurance.mobile.core.network.dto.GoogleLoginRequest

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.insurance.mobile.core.auth.AuthSession
import com.insurance.mobile.core.auth.AuthTokenStore
import com.insurance.mobile.core.network.api.AuthApi
import com.insurance.mobile.core.network.dto.DevLoginRequest
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import retrofit2.HttpException
import javax.inject.Inject

/**
 * Authentication flow for the Android app.
 *
 * Google Sign-In path is intentionally disabled while running on emulators
 * without a Google account (see [signInWithGoogle] below — uncomment to
 * restore). The current active path is [signInDev], which calls
 * ``POST /api/auth/dev-login`` on the backend. That endpoint is only served
 * when the backend has ``ALLOW_DEV_AUTH=true`` and still enforces the
 * allow-list + active checks, so this is safe to leave in code but must be
 * disabled at deploy time by flipping the env var to ``false``.
 */

data class LoginUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val loggedInRole: String? = null,
)

@HiltViewModel
class LoginViewModel @Inject constructor(
    private val authApi: AuthApi,
    private val tokenStore: AuthTokenStore,
) : ViewModel() {

    private val _uiState = MutableStateFlow(LoginUiState())
    val uiState: StateFlow<LoginUiState> = _uiState.asStateFlow()

    /**
     * Dev-only login: ask the backend to mint a session for [email]. The backend
     * rejects unknown / disabled emails, and the endpoint itself 404s unless
     * ``ALLOW_DEV_AUTH=true``.
     */
    fun signInDev(email: String, onSuccess: (AuthSession) -> Unit) {
        val trimmed = email.trim()
        if (trimmed.isEmpty()) {
            _uiState.update { it.copy(error = "Enter an email.") }
            return
        }

        _uiState.update { it.copy(isLoading = true, error = null) }

        viewModelScope.launch {
            try {
                val tokenResp = authApi.loginDev(DevLoginRequest(email = trimmed))
                val session = AuthSession(
                    token = tokenResp.accessToken,
                    userId = tokenResp.user.id,
                    email = tokenResp.user.email,
                    fullName = tokenResp.user.fullName,
                    role = tokenResp.user.role,
                )
                tokenStore.save(session)
                _uiState.update { it.copy(isLoading = false, error = null, loggedInRole = session.role) }
                onSuccess(session)
            } catch (e: HttpException) {
                val detail = runCatching { e.response()?.errorBody()?.string() }.getOrNull().orEmpty()
                val message = when (e.code()) {
                    401 -> parseDetailOrDefault(
                        detail,
                        "This email is not authorized.",
                    )
                    404 -> "Dev sign-in is not enabled on the server. Set ALLOW_DEV_AUTH=true and restart."
                    else -> "Login failed (${e.code()})."
                }
                _uiState.update { it.copy(isLoading = false, error = message) }
            } catch (e: Exception) {
                _uiState.update { it.copy(isLoading = false, error = e.localizedMessage ?: "Login failed.") }
            }
        }
    }

    // ====================================================================
    // Google Sign-In path — commented out while running on the emulator.
    //
    // To re-enable:
    //   1. Uncomment the imports at the top of this file.
    //   2. Uncomment the function below.
    //   3. In LoginScreen.kt, swap the button's onClick back to
    //      viewModel.signInWithGoogle(context) { ... }.
    //   4. Ensure the device has a Google account and that the project has
    //      an Android OAuth client registered with the APK's SHA-1.
    // ====================================================================
    //
    // fun signInWithGoogle(context: Context, onSuccess: (AuthSession) -> Unit) {
    //     val webClientId = BuildConfig.GOOGLE_WEB_CLIENT_ID
    //     if (webClientId.isBlank()) {
    //         _uiState.update {
    //             it.copy(
    //                 isLoading = false,
    //                 error = "Google Sign-In is not configured. Set GOOGLE_WEB_CLIENT_ID in gradle.properties and rebuild.",
    //             )
    //         }
    //         return
    //     }
    //
    //     _uiState.update { it.copy(isLoading = true, error = null) }
    //
    //     viewModelScope.launch {
    //         try {
    //             val credentialManager = CredentialManager.create(context)
    //             val idToken = requestGoogleIdToken(credentialManager, context, webClientId)
    //             val tokenResp = authApi.loginWithGoogle(GoogleLoginRequest(idToken = idToken))
    //             val session = AuthSession(
    //                 token = tokenResp.accessToken,
    //                 userId = tokenResp.user.id,
    //                 email = tokenResp.user.email,
    //                 fullName = tokenResp.user.fullName,
    //                 role = tokenResp.user.role,
    //             )
    //             tokenStore.save(session)
    //             _uiState.update { it.copy(isLoading = false, error = null, loggedInRole = session.role) }
    //             onSuccess(session)
    //         } catch (_: GetCredentialCancellationException) {
    //             _uiState.update { it.copy(isLoading = false, error = null) }
    //         } catch (e: GetCredentialException) {
    //             _uiState.update {
    //                 it.copy(isLoading = false, error = e.localizedMessage ?: "Google Sign-In failed.")
    //             }
    //         } catch (e: HttpException) {
    //             val detail = runCatching { e.response()?.errorBody()?.string() }.getOrNull().orEmpty()
    //             val message = when (e.code()) {
    //                 401 -> parseDetailOrDefault(
    //                     detail,
    //                     "Your Google account is not authorized. Contact an administrator.",
    //                 )
    //                 503 -> "Authentication is not configured on the server."
    //                 else -> "Login failed (${e.code()})."
    //             }
    //             _uiState.update { it.copy(isLoading = false, error = message) }
    //         } catch (e: Exception) {
    //             _uiState.update { it.copy(isLoading = false, error = e.localizedMessage ?: "Login failed.") }
    //         }
    //     }
    // }
    //
    // private suspend fun requestGoogleIdToken(
    //     credentialManager: CredentialManager,
    //     context: Context,
    //     webClientId: String,
    // ): String {
    //     val signInWithExisting = GetGoogleIdOption.Builder()
    //         .setFilterByAuthorizedAccounts(true)
    //         .setServerClientId(webClientId)
    //         .setAutoSelectEnabled(true)
    //         .build()
    //     val signInAnyAccount = GetGoogleIdOption.Builder()
    //         .setFilterByAuthorizedAccounts(false)
    //         .setServerClientId(webClientId)
    //         .build()
    //
    //     val credential = try {
    //         credentialManager
    //             .getCredential(context, GetCredentialRequest(listOf(signInWithExisting)))
    //             .credential
    //     } catch (_: GetCredentialException) {
    //         credentialManager
    //             .getCredential(context, GetCredentialRequest(listOf(signInAnyAccount)))
    //             .credential
    //     }
    //
    //     if (credential !is CustomCredential ||
    //         credential.type != GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL
    //     ) {
    //         throw IllegalStateException("Unexpected credential type: ${credential::class.simpleName}")
    //     }
    //     return GoogleIdTokenCredential.createFrom(credential.data).idToken
    // }

    private fun parseDetailOrDefault(body: String, default: String): String {
        val marker = "\"detail\":\""
        val idx = body.indexOf(marker)
        if (idx == -1) return default
        val start = idx + marker.length
        val end = body.indexOf('"', start)
        if (end == -1) return default
        return body.substring(start, end).ifBlank { default }
    }
}
