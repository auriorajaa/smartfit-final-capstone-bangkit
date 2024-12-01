package com.example.smartfit.network

import com.example.smartfit.BuildConfig
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitClient {
    private val BASE_URL = BuildConfig.API_BASE_URL

    private val okHttpClient = OkHttpClient.Builder()
        .connectTimeout(60, TimeUnit.SECONDS)  // Sesuaikan nilai ini sesuai kebutuhan Anda
        .readTimeout(60, TimeUnit.SECONDS)     // Sesuaikan nilai ini sesuai kebutuhan Anda
        .writeTimeout(60, TimeUnit.SECONDS)    // Sesuaikan nilai ini sesuai kebutuhan Anda
        .build()

    val instance: ApiService by lazy {
        val retrofit = Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        retrofit.create(ApiService::class.java)
    }
}
