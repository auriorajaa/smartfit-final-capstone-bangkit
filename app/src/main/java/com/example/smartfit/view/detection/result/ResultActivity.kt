package com.example.smartfit.view.detection.result

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.drawable.AnimationDrawable
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.view.WindowInsetsController
import android.widget.LinearLayout
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.smartfit.R
import com.example.smartfit.adapter.MixedAdapter
import com.example.smartfit.data.remote.response.StyleRecommendationResponse
import com.example.smartfit.data.remote.retrofit.RetrofitClient
import com.example.smartfit.databinding.ActivityResultBinding
import com.example.smartfit.utils.NotificationHelper
import com.example.smartfit.utils.showUniversalDialog
import com.example.smartfit.view.MainActivity
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
    private val hideHandler = Handler(Looper.getMainLooper())

    private val REQUEST_NOTIFICATION_PERMISSION = 1001

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityResultBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val controller = ViewCompat.getWindowInsetsController(window.decorView)
        controller?.hide(WindowInsetsCompat.Type.navigationBars())
        controller?.systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_DEFAULT

        window.decorView.setOnSystemUiVisibilityChangeListener {
            hideHandler.postDelayed({
                controller?.hide(WindowInsetsCompat.Type.navigationBars())
            }, 5000)
        }

        val constraintLayout: ConstraintLayout = binding.main
        val animationDrawable = constraintLayout.background as AnimationDrawable
        animationDrawable.setEnterFadeDuration(1500)
        animationDrawable.setExitFadeDuration(3000)
        animationDrawable.start()

        window.apply {
            decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN or
                    View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION or
                    View.SYSTEM_UI_FLAG_LAYOUT_STABLE

            statusBarColor = Color.TRANSPARENT

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
        CoroutineScope(Dispatchers.Main).launch {
            binding.progressBar.visibility = View.VISIBLE
        }

        val uidPart = MultipartBody.Part.createFormData("uid", uid)
        val clothingTypePart = MultipartBody.Part.createFormData("clothing_type", clothingType)

        CoroutineScope(Dispatchers.IO).launch {
            val call = RetrofitClient.instance.getStyleRecommendation(image, uidPart, clothingTypePart)
            call.enqueue(object : Callback<StyleRecommendationResponse> {
                override fun onResponse(
                    call: Call<StyleRecommendationResponse>,
                    response: Response<StyleRecommendationResponse>
                ) {
                    CoroutineScope(Dispatchers.Main).launch {
                        binding.progressBar.visibility = View.GONE
                        if (response.isSuccessful) {
                            response.body()?.let {
                                displayResult(it)
                            }
                        } else {
                            showRetryDialog()
                        }
                    }
                }

                override fun onFailure(call: Call<StyleRecommendationResponse>, t: Throwable) {
                    CoroutineScope(Dispatchers.Main).launch {
                        binding.progressBar.visibility = View.GONE
                        showRetryDialog()
                    }
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

        binding.seasonalProbabilityLabel.text = getString(R.string.seasonal_probability_label, result.seasonal_probability)
        binding.skinToneHexLabel.text = getString(R.string.skin_tone_hex_label, result.skin_tone_hex)
        binding.skinToneProbabilityLabel.text = getString(R.string.skin_tone_probability_label, result.skin_tone_probability)
        binding.timestampLabel.text = getString(R.string.timestamp_label, result.timestamp)

        displaySkinToneHexColorBox(result.skin_tone_hex)

        // Periksa izin notifikasi sebelum mengirim
        checkNotificationPermission {
            NotificationHelper.sendNotification(
                this,
                getString(R.string.scan_result_ready),
                getString(R.string.scan_result_message)
            )
        }
    }

    private fun displayColorBoxes(layout: LinearLayout, colors: List<String>) {
        layout.removeAllViews()
        for (color in colors) {
            val colorBox = View(this).apply {
                val drawable = GradientDrawable().apply {
                    shape = GradientDrawable.RECTANGLE
                    setColor(Color.parseColor(color))
                    cornerRadius = 20f
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

    private fun showRetryDialog() {
        showUniversalDialog(
            context = this,
            title = getString(R.string.prediction_failed_title),
            message = getString(R.string.prediction_failed_message),
            positiveButtonText = getString(R.string.retry),
            negativeButtonText = getString(R.string.cancel),
            positiveAction = {
                val intent = Intent(this, CameraActivity::class.java)
                startActivity(intent)
                finish()
            },
            negativeAction = null
        )
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

    private fun checkNotificationPermission(callback: () -> Unit) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(
                    this,
                    arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                    REQUEST_NOTIFICATION_PERMISSION
                )
            } else {
                // Izin sudah diberikan
                callback()
            }
        } else {
            // Izin tidak diperlukan untuk API 30 ke bawah
            callback()
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_NOTIFICATION_PERMISSION) {
            if ((grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED)) {
                // Izin diberikan
                Toast.makeText(this, "Notification permission granted", Toast.LENGTH_SHORT).show()
            } else {
                // Izin tidak diberikan
                Toast.makeText(this, "Notification permission denied", Toast.LENGTH_SHORT).show()
            }
        }
    }
}

