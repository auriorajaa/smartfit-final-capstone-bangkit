package com.example.smartfit.network

import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Call
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Query
import com.google.gson.JsonObject

interface ApiService {
    @Multipart
    @POST("style_recommendation")
    fun getStyleRecommendation(
        @Part image: MultipartBody.Part,
        @Part uid: MultipartBody.Part,
        @Part clothing_type: MultipartBody.Part
    ): Call<StyleRecommendationResponse>

    @GET("get_prediction_history_list")
    fun getPredictionHistoryList(
        @Query("uid") uid: String
    ): Call<JsonObject>

    @Multipart
    @POST("delete_prediction_history")
    fun deletePredictionHistory(
        @Part("uid") uid: RequestBody,
        @Part("prediction_key") predictionKey: RequestBody
    ): Call<JsonObject>
}
