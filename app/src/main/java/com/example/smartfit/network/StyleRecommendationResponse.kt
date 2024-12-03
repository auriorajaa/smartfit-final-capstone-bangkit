package com.example.smartfit.network

import com.google.gson.JsonElement

data class StyleRecommendationResponse(
    val seasonal_color_label: String,
    val skin_tone_label: String,
    val color_palette: JsonElement,
    val seasonal_description: String,
    val seasonal_probability: Double,
    val skin_tone_hex: String,
    val skin_tone_probability: Double,
    val timestamp: String,
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
    val asin: String,
    val delivery: String,
    val description: String,
    val detail_url: String,
    val is_prime: Boolean,
    val pic: String,
    val price: String?,
    val sales_volume: String,
    val title: String
)

data class ColorPalette(
    val dark_colors: List<String>,
    val light_colors: List<String>
)

data class PredictionHistory(
    val prediction_key: String,
    val amazon_products: List<AmazonProduct>,
    val clothing_type: String,
    val color_palette: ColorPalette,
    val outfit_recommendations: List<OutfitRecommendation>,
    val seasonal_color_label: String,
    val seasonal_description: String,
    val seasonal_probability: Double,
    val skin_tone_hex: String,
    val skin_tone_label: String,
    val skin_tone_probability: Double,
    val timestamp: String,
    val user_uid: String
)
