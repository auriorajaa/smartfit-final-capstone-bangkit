package com.example.smartfit.view.detection.result

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.smartfit.databinding.ActivityDetailBinding
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
import android.graphics.drawable.AnimationDrawable
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.view.WindowInsetsController
import android.widget.LinearLayout
import com.example.smartfit.R
import com.example.smartfit.adapter.MixedAdapter
import com.example.smartfit.data.remote.response.AmazonProduct
import com.example.smartfit.data.remote.response.OutfitRecommendation
import com.example.smartfit.data.remote.retrofit.RetrofitClient
import android.graphics.drawable.GradientDrawable
import androidx.constraintlayout.widget.ConstraintLayout

class DetailActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDetailBinding
    private lateinit var mixedAdapter: MixedAdapter
    private lateinit var handler: Handler
    private var scrollPosition = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDetailBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Mengatur background animasi
        val constraintLayout: ConstraintLayout = binding.main
        val animationDrawable = constraintLayout.background as AnimationDrawable
        animationDrawable.setEnterFadeDuration(1500)
        animationDrawable.setExitFadeDuration(3000)
        animationDrawable.start()

        window.apply {
            // Membuat status bar dan navigation bar transparan
            decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN or
                    View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION or
                    View.SYSTEM_UI_FLAG_LAYOUT_STABLE

            // Pastikan warna mengikuti latar belakang Activity
            statusBarColor = Color.TRANSPARENT

            // Menyesuaikan ikon status bar dan navigation bar
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                insetsController?.setSystemBarsAppearance(
                    WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS or
                            WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS,
                    WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS or
                            WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS
                )
            }
        }

        val predictionKey = intent.getStringExtra("PREDICTION_KEY")
        val userId = intent.getStringExtra("USER_ID")

        binding.mixedRecyclerView.layoutManager =
            LinearLayoutManager(this, LinearLayoutManager.HORIZONTAL, false)

        fetchPredictionHistoryDetail(userId, predictionKey)

        handler = Handler(Looper.getMainLooper())
    }

    private fun fetchPredictionHistoryDetail(userId: String?, predictionKey: String?) {
        if (userId == null || predictionKey == null) {
            Toast.makeText(this, getString(R.string.missing_user_or_prediction), Toast.LENGTH_SHORT).show()
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
                        Log.e("DetailActivity", getString(R.string.error_retrieving_data) + ": ${response.message()}")
                    }
                }

                override fun onFailure(call: Call<JsonObject>, t: Throwable) {
                    Log.e("DetailActivity", getString(R.string.error_fetching_data, t.message))
                }
            })
        }
    }

    private fun displayDetail(predictionData: JsonObject) {
        binding.seasonalColorLabel.text = predictionData.get("seasonal_color_label")?.asString ?: getString(R.string.not_available)
        binding.skinToneLabel.text = predictionData.get("skin_tone_label")?.asString ?: getString(R.string.not_available)
        binding.seasonalDescription.text = predictionData.get("seasonal_description")?.asString ?: getString(R.string.not_available)

        predictionData.getAsJsonObject("color_palette")?.let { colorPalette ->
            displayColorBoxes(binding.darkColorsLayout, colorPalette.getAsJsonArray("dark_colors")?.map { it.asString } ?: emptyList())
            displayColorBoxes(binding.lightColorsLayout, colorPalette.getAsJsonArray("light_colors")?.map { it.asString } ?: emptyList())
        }

        val amazonProducts = predictionData.getAsJsonArray("amazon_products")?.map {
            val product = it.asJsonObject
            AmazonProduct(
                asin = product.get("asin")?.asString ?: getString(R.string.not_available),
                delivery = product.get("delivery")?.asString ?: getString(R.string.not_available),
                description = product.get("description")?.asString ?: getString(R.string.not_available),
                detail_url = product.get("detail_url")?.asString ?: "",
                is_prime = product.get("is_prime")?.asBoolean ?: false,
                pic = product.get("pic")?.asString ?: "",
                price = product.get("price")?.asString,
                sales_volume = product.get("sales_volume")?.asString ?: getString(R.string.not_available),
                title = product.get("title")?.asString ?: getString(R.string.not_available)
            )
        } ?: emptyList()

        val outfitRecommendations = predictionData.getAsJsonArray("outfit_recommendations")?.map {
            val item = it.asJsonObject
            OutfitRecommendation(item.get("item")?.asString ?: getString(R.string.not_available), item.get("description")?.asString ?: getString(R.string.not_available))
        } ?: emptyList()

        mixedAdapter = MixedAdapter(this, amazonProducts, outfitRecommendations)
        binding.mixedRecyclerView.adapter = mixedAdapter
        startAutoScroll()

        binding.seasonalProbabilityLabel.text = getString(R.string.seasonal_probability_label, predictionData.get("seasonal_probability")?.asDouble ?: 0.0)
        binding.skinToneHexLabel.text = getString(R.string.skin_tone_hex_label, predictionData.get("skin_tone_hex")?.asString ?: getString(R.string.not_available))
        binding.skinToneProbabilityLabel.text = getString(R.string.skin_tone_probability_label, predictionData.get("skin_tone_probability")?.asDouble ?: 0.0)
        binding.timestampLabel.text = getString(R.string.timestamp_label, predictionData.get("timestamp")?.asString ?: getString(R.string.not_available))

        displaySkinToneHexColorBox(predictionData.get("skin_tone_hex")?.asString ?: "#FFFFFF")
    }


    private fun displayColorBoxes(layout: LinearLayout, colors: List<String>) {
        layout.removeAllViews()
        for (color in colors) {
            val colorBox = View(this).apply {
                // Create a GradientDrawable with rounded corners
                val drawable = GradientDrawable().apply {
                    shape = GradientDrawable.RECTANGLE
                    setColor(Color.parseColor(color))
                    cornerRadius = 20f // Adjust the corner radius as needed
                }
                background = drawable
                layoutParams = LinearLayout.LayoutParams(110, 110).apply {
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
