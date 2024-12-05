package com.example.smartfit

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.smartfit.databinding.ActivityDetailBinding
import com.example.smartfit.network.RetrofitClient
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import com.google.gson.JsonObject
import android.util.Log
import android.widget.Toast
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import android.view.View
import android.graphics.Color
import android.os.Handler
import android.os.Looper
import android.widget.LinearLayout
import com.example.smartfit.network.AmazonProduct
import com.example.smartfit.network.OutfitRecommendation

class DetailActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDetailBinding
    private lateinit var mixedAdapter: MixedAdapter
    private lateinit var handler: Handler
    private var scrollPosition = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDetailBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val predictionKey = intent.getStringExtra("PREDICTION_KEY")
        val userId = intent.getStringExtra("USER_ID")

        binding.mixedRecyclerView.layoutManager =
            LinearLayoutManager(this, LinearLayoutManager.HORIZONTAL, false)

        fetchPredictionHistoryDetail(userId, predictionKey)

        handler = Handler(Looper.getMainLooper())
    }

    private fun fetchPredictionHistoryDetail(userId: String?, predictionKey: String?) {
        if (userId == null || predictionKey == null) {
            Toast.makeText(this, "Missing user ID or prediction key", Toast.LENGTH_SHORT).show()
            return
        }

        CoroutineScope(Dispatchers.IO).launch {
            val call = RetrofitClient.instance.getPredictionHistoryDetail(userId, predictionKey)
            call.enqueue(object : Callback<JsonObject> {
                override fun onResponse(call: Call<JsonObject>, response: Response<JsonObject>) {
                    if (response.isSuccessful) {
                        response.body()?.let {
                            val predictionData = it.getAsJsonObject("prediction_data")
                            runOnUiThread {
                                displayDetail(predictionData)
                            }
                        }
                    } else {
                        Log.e("DetailActivity", "Failed to retrieve data: ${response.message()}")
                    }
                }

                override fun onFailure(call: Call<JsonObject>, t: Throwable) {
                    Log.e("DetailActivity", "Error: ${t.message}")
                }
            })
        }
    }

    private fun displayDetail(predictionData: JsonObject) {
        binding.seasonalColorLabel.text = predictionData.get("seasonal_color_label")?.asString ?: "N/A"
        binding.skinToneLabel.text = predictionData.get("skin_tone_label")?.asString ?: "N/A"
        binding.seasonalDescription.text = predictionData.get("seasonal_description")?.asString ?: "N/A"

        predictionData.getAsJsonObject("color_palette")?.let { colorPalette ->
            displayColorBoxes(binding.darkColorsLayout, colorPalette.getAsJsonArray("dark_colors")?.map { it.asString } ?: emptyList())
            displayColorBoxes(binding.lightColorsLayout, colorPalette.getAsJsonArray("light_colors")?.map { it.asString } ?: emptyList())
        }

        val amazonProducts = predictionData.getAsJsonArray("amazon_products")?.map {
            val product = it.asJsonObject
            AmazonProduct(
                asin = product.get("asin")?.asString ?: "N/A",
                delivery = product.get("delivery")?.asString ?: "N/A",
                description = product.get("description")?.asString ?: "N/A",
                detail_url = product.get("detail_url")?.asString ?: "",
                is_prime = product.get("is_prime")?.asBoolean ?: false,
                pic = product.get("pic")?.asString ?: "",
                price = product.get("price")?.asString,
                sales_volume = product.get("sales_volume")?.asString ?: "N/A",
                title = product.get("title")?.asString ?: "N/A"
            )
        } ?: emptyList()

        val outfitRecommendations = predictionData.getAsJsonArray("outfit_recommendations")?.map {
            val item = it.asJsonObject
            OutfitRecommendation(item.get("item")?.asString ?: "N/A", item.get("description")?.asString ?: "N/A")
        } ?: emptyList()

        mixedAdapter = MixedAdapter(this, amazonProducts, outfitRecommendations)
        binding.mixedRecyclerView.adapter = mixedAdapter
        startAutoScroll()

        binding.seasonalProbabilityLabel.text = "Seasonal Probability: ${predictionData.get("seasonal_probability")?.asDouble ?: 0.0}%"
        binding.skinToneHexLabel.text = "Skin Tone Hex: ${predictionData.get("skin_tone_hex")?.asString ?: "N/A"}"
        binding.skinToneProbabilityLabel.text = "Skin Tone Probability: ${predictionData.get("skin_tone_probability")?.asDouble ?: 0.0}%"
        binding.timestampLabel.text = "Timestamp: ${predictionData.get("timestamp")?.asString ?: "N/A"}"

        displaySkinToneHexColorBox(predictionData.get("skin_tone_hex")?.asString ?: "#FFFFFF")
    }

    private fun displayColorBoxes(layout: LinearLayout, colors: List<String>) {
        layout.removeAllViews()
        for (color in colors) {
            val colorBox = View(this).apply {
                setBackgroundColor(Color.parseColor(color))
                layoutParams = LinearLayout.LayoutParams(150, 150).apply {
                    setMargins(20, 20, 20, 20)
                }
            }
            layout.addView(colorBox)
        }
    }

    private fun displaySkinToneHexColorBox(hexColor: String) {
        val colorBox = binding.skinToneHexColorBox
        colorBox.setBackgroundColor(Color.parseColor(hexColor))
    }

    private fun startAutoScroll() {
        handler.postDelayed(object : Runnable {
            override fun run() {
                scrollPosition++
                if (scrollPosition == mixedAdapter.itemCount) {
                    scrollPosition = 0
                }
                binding.mixedRecyclerView.smoothScrollToPosition(scrollPosition)
                handler.postDelayed(this, 2000)
            }
        }, 2000)
    }

    override fun onDestroy() {
        super.onDestroy()
        handler.removeCallbacksAndMessages(null)
    }
}
