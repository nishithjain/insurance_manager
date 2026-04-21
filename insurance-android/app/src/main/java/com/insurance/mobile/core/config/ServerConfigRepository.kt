package com.insurance.mobile.core.config

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.util.concurrent.atomic.AtomicReference
import javax.inject.Inject
import javax.inject.Singleton

private val Context.serverConfigDataStore: DataStore<Preferences> by preferencesDataStore(
    name = "server_config",
)

private val KEY_API_BASE_URL = stringPreferencesKey("api_base_url_normalized")

/**
 * Persists and caches the configured API base URL (e.g. `http://192.168.1.10:5000/api/`).
 */
@Singleton
class ServerConfigRepository @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private val dataStore get() = context.serverConfigDataStore

    private val mutex = Mutex()
    private val cached = AtomicReference<String?>(null)

    val baseUrlFlow: Flow<String?> = dataStore.data.map { prefs ->
        prefs[KEY_API_BASE_URL]
    }

    /**
     * Loads from disk into memory. Call from startup before API usage.
     */
    suspend fun hydrate(): String? = mutex.withLock {
        val fromDisk = dataStore.data.map { it[KEY_API_BASE_URL] }.first()
        cached.set(fromDisk)
        fromDisk
    }

    /** In-memory value after [hydrate] or [saveBaseUrl]. */
    fun getCachedBaseUrl(): String? = cached.get()

    suspend fun saveBaseUrl(rawInput: String): Result<String> {
        return try {
            val normalized = ApiUrlNormalizer.requireNormalized(rawInput)
            dataStore.edit { it[KEY_API_BASE_URL] = normalized }
            cached.set(normalized)
            Result.success(normalized)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun clearBaseUrl() {
        dataStore.edit { it.remove(KEY_API_BASE_URL) }
        cached.set(null)
    }
}
