package com.example.smartfit.network

import com.google.gson.JsonElement

data class StyleRecommendationResponse(
    val seasonal_color_label: String,
    val skin_tone_label: String,
    val color_palette: JsonElement, // Menggunakan JsonElement untuk menangani variasi
    val seasonal_description: String,
    val outfit_recommendations: List<OutfitRecommendation>,
    val amazon_products: List<AmazonProduct>,
    val clothing_type: String,
    val user_uid: String,
    val firebase_key: String
)

data class OutfitRecommendation(
    val item: String,
    val description: String
)

data class AmazonProduct(
    val title: String,
    val price: String,
    val url: String,
    val description: String
)
