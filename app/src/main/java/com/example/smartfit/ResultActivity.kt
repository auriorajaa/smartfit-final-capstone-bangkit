package com.example.smartfit

import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.LinearLayout
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.smartfit.databinding.ActivityResultBinding
import com.example.smartfit.network.RetrofitClient
import com.example.smartfit.network.StyleRecommendationResponse
import com.example.smartfit.utils.NotificationHelper
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
    private lateinit var amazonProductAdapter: AmazonProductAdapter
    private lateinit var outfitRecommendationAdapter: OutfitRecommendationAdapter
    private lateinit var handler: Handler
    private var amazonScrollPosition = 0
    private var outfitScrollPosition = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityResultBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val imagePath = intent.getStringExtra("IMAGE_PATH")
        val uid = intent.getStringExtra("UID") ?: "unknown_user"
        val clothingType = intent.getStringExtra("CLOTHING_TYPE") ?: "streetwear"

        // Atur LinearLayoutManager horizontal untuk AmazonProducts
        binding.amazonProducts.layoutManager = LinearLayoutManager(this, LinearLayoutManager.HORIZONTAL, false)
        binding.outfitRecommendations.layoutManager = LinearLayoutManager(this, LinearLayoutManager.HORIZONTAL, false)

        imagePath?.let {
            val imageFile = File(it)
            if (imageFile.exists()) {
                val requestFile = RequestBody.create("image/jpeg".toMediaTypeOrNull(), imageFile)
                val body = MultipartBody.Part.createFormData("image", imageFile.name, requestFile)
                sendRequest(body, uid, clothingType)
            }
        }

        // Inisialisasi Handler untuk menggerakkan RecyclerView
        handler = Handler(Looper.getMainLooper())
    }

    private fun sendRequest(image: MultipartBody.Part, uid: String, clothingType: String) {
        val uidPart = MultipartBody.Part.createFormData("uid", uid)
        val clothingTypePart = MultipartBody.Part.createFormData("clothing_type", clothingType)

        CoroutineScope(Dispatchers.IO).launch {
            val call = RetrofitClient.instance.getStyleRecommendation(image, uidPart, clothingTypePart)
            call.enqueue(object : Callback<StyleRecommendationResponse> {
                override fun onResponse(call: Call<StyleRecommendationResponse>, response: Response<StyleRecommendationResponse>) {
                    if (response.isSuccessful) {
                        response.body()?.let {
                            CoroutineScope(Dispatchers.Main).launch {
                                displayResult(it)
                            }
                        }
                    } else {
                        showRetryDialog()
                    }
                }

                override fun onFailure(call: Call<StyleRecommendationResponse>, t: Throwable) {
                    showRetryDialog()
                }
            })
        }
    }

    private fun displayResult(result: StyleRecommendationResponse) {
        binding.seasonalColorLabel.text = result.seasonal_color_label
        binding.skinToneLabel.text = result.skin_tone_label
        binding.seasonalDescription.text = result.seasonal_description

        if (result.color_palette.isJsonObject) {
            val paletteObject = result.color_palette.asJsonObject
            val darkColors = paletteObject["dark_colors"].asJsonArray.map { it.asString }
            val lightColors = paletteObject["light_colors"].asJsonArray.map { it.asString }
            displayColorBoxes(binding.darkColorsLayout, darkColors)
            displayColorBoxes(binding.lightColorsLayout, lightColors)
        }

        outfitRecommendationAdapter = OutfitRecommendationAdapter(result.outfit_recommendations)
        binding.outfitRecommendations.adapter = outfitRecommendationAdapter
        startAutoScrollOutfits()

        amazonProductAdapter = AmazonProductAdapter(this, result.amazon_products)
        binding.amazonProducts.adapter = amazonProductAdapter
        startAutoScrollAmazon()

        binding.seasonalProbabilityLabel.text = "Seasonal Probability: ${result.seasonal_probability}%"
        binding.skinToneHexLabel.text = "Skin Tone Hex: ${result.skin_tone_hex}"
        binding.skinToneProbabilityLabel.text = "Skin Tone Probability: ${result.skin_tone_probability}%"
        binding.timestampLabel.text = "Timestamp: ${result.timestamp}"

        // Kirim notifikasi setelah hasil scan ditampilkan
        NotificationHelper.sendNotification(
            this,
            "Scan Result Ready!",
            "Hasil scan telah tersedia. Cek rekomendasi gaya terbaru Anda sekarang!"
        )
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

    private fun showRetryDialog() {
        AlertDialog.Builder(this)
            .setTitle("Prediction Failed")
            .setMessage("The prediction process failed. Please try scanning with a different image.")
            .setPositiveButton("Retry") { _, _ ->
                val intent = Intent(this, ChooseActivity::class.java)
                startActivity(intent)
                finish()
            }
            .setNegativeButton("Cancel") { dialog, _ ->
                dialog.dismiss()
            }
            .show()
    }

    private fun startAutoScrollAmazon() {
        handler.postDelayed(object : Runnable {
            override fun run() {
                amazonScrollPosition++
                if (amazonScrollPosition == amazonProductAdapter.itemCount) {
                    amazonScrollPosition = 0
                }
                binding.amazonProducts.smoothScrollToPosition(amazonScrollPosition)
                handler.postDelayed(this, 2000)
            }
        }, 2000)
    }

    private fun startAutoScrollOutfits() {
        handler.postDelayed(object : Runnable {
            override fun run() {
                if (::outfitRecommendationAdapter.isInitialized) {
                    outfitScrollPosition++
                    if (outfitScrollPosition == outfitRecommendationAdapter.itemCount) {
                        outfitScrollPosition = 0
                    }
                    binding.outfitRecommendations.smoothScrollToPosition(outfitScrollPosition)
                }
                handler.postDelayed(this, 2000)
            }
        }, 2000)
    }

    override fun onDestroy() {
        super.onDestroy()
        handler.removeCallbacksAndMessages(null)
    }
}
