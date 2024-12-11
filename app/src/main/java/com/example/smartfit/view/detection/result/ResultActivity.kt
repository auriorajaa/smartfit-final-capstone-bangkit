package com.example.smartfit.view.detection.result

import android.content.Intent
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.view.WindowInsetsController
import android.widget.LinearLayout
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.smartfit.adapter.MixedAdapter
import com.example.smartfit.data.remote.response.StyleRecommendationResponse
import com.example.smartfit.data.remote.retrofit.RetrofitClient
import com.example.smartfit.databinding.ActivityResultBinding
import com.example.smartfit.utils.NotificationHelper
import com.example.smartfit.view.MainActivity
import com.example.smartfit.view.credentials.register.RegisterActivity
import com.example.smartfit.view.detection.camera.CameraActivity
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
    private lateinit var mixedAdapter: MixedAdapter
    private lateinit var handler: Handler
    private var scrollPosition = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityResultBinding.inflate(layoutInflater)
        setContentView(binding.root)

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

        val imagePath = intent.getStringExtra("IMAGE_PATH")
        val uid = intent.getStringExtra("UID") ?: "unknown_user"
        val clothingType = intent.getStringExtra("CLOTHING_TYPE") ?: "streetwear"

        binding.mixedRecyclerView.layoutManager =
            LinearLayoutManager(this, LinearLayoutManager.HORIZONTAL, false)

        imagePath?.let {
            val imageFile = File(it)
            if (imageFile.exists()) {
                val requestFile = RequestBody.create("image/jpeg".toMediaTypeOrNull(), imageFile)
                val body = MultipartBody.Part.createFormData("image", imageFile.name, requestFile)
                sendRequest(body, uid, clothingType)
            }
        }

        handler = Handler(Looper.getMainLooper())

        binding.btnFinishResult.setOnClickListener {
            val intent = Intent(this, MainActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
            startActivity(intent)
        }
    }

    private fun sendRequest(image: MultipartBody.Part, uid: String, clothingType: String) {
        val uidPart = MultipartBody.Part.createFormData("uid", uid)
        val clothingTypePart = MultipartBody.Part.createFormData("clothing_type", clothingType)

        CoroutineScope(Dispatchers.IO).launch {
            val call =
                RetrofitClient.instance.getStyleRecommendation(image, uidPart, clothingTypePart)
            call.enqueue(object : Callback<StyleRecommendationResponse> {
                override fun onResponse(
                    call: Call<StyleRecommendationResponse>,
                    response: Response<StyleRecommendationResponse>
                ) {
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

        mixedAdapter = MixedAdapter(this, result.amazon_products, result.outfit_recommendations)
        binding.mixedRecyclerView.adapter = mixedAdapter
        startAutoScroll()

        binding.seasonalProbabilityLabel.text = "Seasonal Probability: ${result.seasonal_probability}%"
        binding.skinToneHexLabel.text = "Skin Tone Hex: ${result.skin_tone_hex}"
        binding.skinToneProbabilityLabel.text = "Skin Tone Probability: ${result.skin_tone_probability}%"
        binding.timestampLabel.text = "Timestamp: ${result.timestamp}"

        displaySkinToneHexColorBox(result.skin_tone_hex)

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

    private fun displaySkinToneHexColorBox(hexColor: String) {
        val colorBox = binding.skinToneHexColorBox
        colorBox.setBackgroundColor(Color.parseColor(hexColor))
    }

    private fun showRetryDialog() {
        AlertDialog.Builder(this)
            .setTitle("Prediction Failed")
            .setMessage("The prediction process failed. Please try scanning with a different image.")
            .setPositiveButton("Retry") { _, _ ->
                val intent = Intent(this, CameraActivity::class.java)
                startActivity(intent)
                finish()
            }
            .setNegativeButton("Cancel") { dialog, _ ->
                dialog.dismiss()
            }
            .show()
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
