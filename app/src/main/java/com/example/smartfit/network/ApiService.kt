package com.example.smartfit.network

import okhttp3.MultipartBody
import retrofit2.Call
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part

interface ApiService {
    @Multipart
    @POST("style_recommendation")
    fun getStyleRecommendation(
        @Part image: MultipartBody.Part,
        @Part uid: MultipartBody.Part,
        @Part clothing_type: MultipartBody.Part
    ): Call<StyleRecommendationResponse>
}
