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
import com.google.gson.JsonElement
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
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

        binding.outfitRecommendations.layoutManager = LinearLayoutManager(this)
        binding.outfitRecommendations.adapter = OutfitRecommendationAdapter(emptyList())

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
        CoroutineScope(Dispatchers.IO).launch {
            val call = RetrofitClient.instance.getStyleRecommendation(image, uid, clothingType)
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

        val adapter = OutfitRecommendationAdapter(result.outfit_recommendations)
        binding.outfitRecommendations.adapter = adapter
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
