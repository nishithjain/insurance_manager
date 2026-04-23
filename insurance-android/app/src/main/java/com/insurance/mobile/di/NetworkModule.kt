package com.insurance.mobile.di

import com.insurance.mobile.BuildConfig
import com.insurance.mobile.core.auth.AuthInterceptor
import com.insurance.mobile.core.network.DynamicHostInterceptor
import com.insurance.mobile.core.network.api.AuthApi
import com.insurance.mobile.core.network.api.CustomerApi
import com.insurance.mobile.core.network.api.PolicyApi
import com.insurance.mobile.core.network.api.RenewalApi
import com.insurance.mobile.core.network.api.StatisticsApi
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

/**
 * Wires OkHttp (dynamic host, logging), Moshi, Retrofit, and API interfaces.
 */
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideMoshi(): Moshi =
        Moshi.Builder()
            .addLast(KotlinJsonAdapterFactory())
            .build()

    @Provides
    @Singleton
    fun provideLoggingInterceptor(): HttpLoggingInterceptor =
        HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) {
                HttpLoggingInterceptor.Level.BODY
            } else {
                HttpLoggingInterceptor.Level.NONE
            }
        }

    @Provides
    @Singleton
    fun provideOkHttpClient(
        loggingInterceptor: HttpLoggingInterceptor,
        dynamicHostInterceptor: DynamicHostInterceptor,
        authInterceptor: AuthInterceptor,
    ): OkHttpClient =
        OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            // Order matters: rewrite host first, then stamp the Authorization
            // header so the logger can record the final outgoing request.
            .addInterceptor(dynamicHostInterceptor)
            .addInterceptor(authInterceptor)
            .addInterceptor(loggingInterceptor)
            .build()

    @Provides
    @Singleton
    fun provideRetrofit(
        okHttpClient: OkHttpClient,
        moshi: Moshi,
    ): Retrofit =
        Retrofit.Builder()
            .baseUrl(BuildConfig.PLACEHOLDER_API_BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()

    @Provides
    fun providePolicyApi(retrofit: Retrofit): PolicyApi =
        retrofit.create(PolicyApi::class.java)

    @Provides
    fun provideCustomerApi(retrofit: Retrofit): CustomerApi =
        retrofit.create(CustomerApi::class.java)

    @Provides
    fun provideStatisticsApi(retrofit: Retrofit): StatisticsApi =
        retrofit.create(StatisticsApi::class.java)

    @Provides
    fun provideRenewalApi(retrofit: Retrofit): RenewalApi =
        retrofit.create(RenewalApi::class.java)

    @Provides
    fun provideAuthApi(retrofit: Retrofit): AuthApi =
        retrofit.create(AuthApi::class.java)
}
