package com.insurance.mobile.core.auth

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import java.util.concurrent.atomic.AtomicReference
import javax.inject.Inject
import javax.inject.Singleton

private val Context.authDataStore: DataStore<Preferences> by preferencesDataStore(name = "auth_session")

private val KEY_JWT = stringPreferencesKey("jwt_access_token")
private val KEY_USER_ID = intPreferencesKey("auth_user_id")
private val KEY_USER_EMAIL = stringPreferencesKey("auth_user_email")
private val KEY_USER_NAME = stringPreferencesKey("auth_user_name")
private val KEY_USER_ROLE = stringPreferencesKey("auth_user_role")

/**
 * Snapshot of the current auth session as seen by the client.
 *
 * We keep a tiny cache of user fields beside the JWT so the UI can render
 * the signed-in identity without a network round-trip. The server remains
 * the source of truth (/auth/me) — this cache is purely for UX responsiveness.
 */
data class AuthSession(
    val token: String,
    val userId: Int,
    val email: String,
    val fullName: String,
    val role: String,
) {
    val isAdmin: Boolean get() = role.equals("admin", ignoreCase = true)
}

/**
 * Persistent store for the backend-issued JWT plus a minimal user snapshot.
 *
 * Symmetric with [com.insurance.mobile.core.config.ServerConfigRepository]:
 * a ``hydrate()`` call warms an in-memory cache so the OkHttp interceptor
 * can read the token synchronously on every request without blocking on
 * DataStore's coroutine API.
 */
@Singleton
class AuthTokenStore @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private val dataStore get() = context.authDataStore
    private val cached = AtomicReference<AuthSession?>(null)

    val sessionFlow: Flow<AuthSession?> = dataStore.data
        .map { prefs ->
            val token = prefs[KEY_JWT] ?: return@map null
            AuthSession(
                token = token,
                userId = prefs[KEY_USER_ID] ?: 0,
                email = prefs[KEY_USER_EMAIL].orEmpty(),
                fullName = prefs[KEY_USER_NAME].orEmpty(),
                role = prefs[KEY_USER_ROLE].orEmpty(),
            )
        }
        .distinctUntilChanged()

    /** Warm the in-memory cache. Call once during app startup. */
    suspend fun hydrate(): AuthSession? {
        val fromDisk = sessionFlow.first()
        cached.set(fromDisk)
        return fromDisk
    }

    /** Synchronously readable for OkHttp interceptors. */
    fun getCachedSession(): AuthSession? = cached.get()

    suspend fun save(session: AuthSession) {
        dataStore.edit { prefs ->
            prefs[KEY_JWT] = session.token
            prefs[KEY_USER_ID] = session.userId
            prefs[KEY_USER_EMAIL] = session.email
            prefs[KEY_USER_NAME] = session.fullName
            prefs[KEY_USER_ROLE] = session.role
        }
        cached.set(session)
    }

    suspend fun clear() {
        dataStore.edit { it.clear() }
        cached.set(null)
    }
}
