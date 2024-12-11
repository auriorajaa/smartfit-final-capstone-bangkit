package com.example.smartfit.view.detection.camera2


import android.content.Intent
import android.graphics.Color
import android.graphics.drawable.AnimationDrawable
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.View
import android.view.WindowInsetsController
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import com.example.smartfit.databinding.ActivityCamera2Binding
import com.example.smartfit.view.detection.camera.CameraActivity
import com.example.smartfit.view.detection.gender.GenderActivity

class Camera2Activity : AppCompatActivity() {

    private lateinit var binding: ActivityCamera2Binding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityCamera2Binding.inflate(layoutInflater)
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

        val croppedImageUriString = intent.getStringExtra("CROPPED_IMAGE_URI")
        val croppedImageUri = Uri.parse(croppedImageUriString)
        binding.ivPlaceHolderImage.setImageURI(croppedImageUri)

        binding.btnNextCamera2.setOnClickListener {
            val intent = Intent(this, GenderActivity::class.java).apply {
                putExtra("CROPPED_IMAGE_URI", croppedImageUri.toString())
            }
            startActivity(intent)
        }

        binding.btnRetakeCamera2.setOnClickListener {
            val intent = Intent(this, CameraActivity::class.java)
            startActivity(intent)
        }
    }
}
