package com.example.smartfit

import android.graphics.Color
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.LinearLayout
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.smartfit.databinding.ActivityResultBinding
import com.example.smartfit.network.RetrofitClient
import com.example.smartfit.network.StyleRecommendationResponse
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.io.File

class ResultActivity : AppCompatActivity() {

    private lateinit var binding: ActivityResultBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityResultBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val imagePath = intent.getStringExtra("IMAGE_PATH")
        val uid = intent.getStringExtra("UID") ?: "unknown_user"
        val clothingType = intent.getStringExtra("CLOTHING_TYPE") ?: "streetwear"
        Log.d("ResultActivity", "Received clothingType: $clothingType")

        binding.outfitRecommendations.layoutManager = LinearLayoutManager(this)
        binding.amazonProducts.layoutManager = LinearLayoutManager(this)

        imagePath?.let {
            val imageFile = File(it)
            if (imageFile.exists()) {
                val requestFile = RequestBody.create("image/jpeg".toMediaTypeOrNull(), imageFile)
                val body = MultipartBody.Part.createFormData("image", imageFile.name, requestFile)
                sendRequest(body, uid, clothingType)
            }
        }
    }

    private fun sendRequest(image: MultipartBody.Part, uid: String, clothingType: String) {
        Log.d("ResultActivity", "Sending request with UID: $uid, ClothingType: $clothingType, Image: ${image.body.contentLength()} bytes")

        val uidPart = MultipartBody.Part.createFormData("uid", uid)
        val clothingTypePart = MultipartBody.Part.createFormData("clothing_type", clothingType)

        CoroutineScope(Dispatchers.IO).launch {
            val call = RetrofitClient.instance.getStyleRecommendation(image, uidPart, clothingTypePart)
            Log.d("ResultActivity", "Sending request with UID: $uid, ClothingType: $clothingType, Image: ${image.body.contentLength()} bytes")
            call.enqueue(object : Callback<StyleRecommendationResponse> {
                override fun onResponse(call: Call<StyleRecommendationResponse>, response: Response<StyleRecommendationResponse>) {
                    Log.d("ResultActivity", "Response: ${response.raw()}")
                    if (response.isSuccessful) {
                        response.body()?.let {
                            Log.d("ResultActivity", "Response body: $it")
                            CoroutineScope(Dispatchers.Main).launch {
                                displayResult(it)
                            }
                        }
                    } else {
                        Log.e("ResultActivity", "Request failed with code: ${response.code()} and message: ${response.message()}")
                        Log.e("ResultActivity", "Response: ${response.errorBody()?.string()}")
                    }
                }

                override fun onFailure(call: Call<StyleRecommendationResponse>, t: Throwable) {
                    Log.e("ResultActivity", "Request failed", t)
                }
            })
        }
    }

    private fun displayResult(result: StyleRecommendationResponse) {
        binding.seasonalColorLabel.text = result.seasonal_color_label
        binding.skinToneLabel.text = result.skin_tone_label
        binding.seasonalDescription.text = result.seasonal_description

        // Menangani color_palette yang bisa berupa string atau array
        when {
            result.color_palette.isJsonObject -> {
                val paletteObject = result.color_palette.asJsonObject

                val darkColors = paletteObject["dark_colors"].asJsonArray.map { it.asString }
                val lightColors = paletteObject["light_colors"].asJsonArray.map { it.asString }

                displayColorBoxes(binding.darkColorsLayout, darkColors)
                displayColorBoxes(binding.lightColorsLayout, lightColors)
            }
        }

        val outfitAdapter = OutfitRecommendationAdapter(result.outfit_recommendations)
        binding.outfitRecommendations.adapter = outfitAdapter

        val amazonProductAdapter = AmazonProductAdapter(this, result.amazon_products)
        binding.amazonProducts.adapter = amazonProductAdapter

        binding.seasonalProbabilityLabel.text = "Seasonal Probability: ${result.seasonal_probability}%"
        binding.skinToneHexLabel.text = "Skin Tone Hex: ${result.skin_tone_hex}"
        binding.skinToneProbabilityLabel.text = "Skin Tone Probability: ${result.skin_tone_probability}%"
        binding.timestampLabel.text = "Timestamp: ${result.timestamp}"
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
}
