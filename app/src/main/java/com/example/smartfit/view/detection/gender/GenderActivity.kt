package com.example.smartfit.view.detection.gender

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
import com.example.smartfit.databinding.ActivityGenderBinding
import com.example.smartfit.view.detection.result.ResultActivity
import com.google.firebase.auth.FirebaseAuth

class GenderActivity : AppCompatActivity() {

    private lateinit var binding: ActivityGenderBinding
    private var selectedGender: String? = null
    private lateinit var croppedImageUri: Uri

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityGenderBinding.inflate(layoutInflater)
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
        croppedImageUri = Uri.parse(croppedImageUriString)

        binding.cvMaleGender.setOnClickListener {
            selectedGender = "men"
            binding.containerClothingType.visibility = View.VISIBLE
            binding.genderContainer.visibility = View.GONE
            binding.cvMaleGender.visibility = View.GONE
            binding.cvFemaleGender.visibility = View.GONE
        }

        binding.cvFemaleGender.setOnClickListener {
            selectedGender = "women"
            binding.containerClothingType.visibility = View.VISIBLE
            binding.genderContainer.visibility = View.GONE
            binding.cvMaleGender.visibility = View.GONE
            binding.cvFemaleGender.visibility = View.GONE
        }

        binding.cvFormal.setOnClickListener {
            proceedToResult("formal")
        }

        binding.cvWedding.setOnClickListener {
            proceedToResult("wedding")
        }

        binding.cvStreetwear.setOnClickListener {
            proceedToResult("streetwear")
        }

        binding.cvPajamas.setOnClickListener {
            proceedToResult("pajamas")
        }

        binding.cvVintage.setOnClickListener {
            proceedToResult("vintage")
        }

        binding.cvCasual.setOnClickListener {
            proceedToResult("casual")
        }

        binding.cvSportwear.setOnClickListener {
            proceedToResult("sportswear")
        }
    }

    private fun proceedToResult(clothingType: String) {
        val user = FirebaseAuth.getInstance().currentUser
        val uid = user?.uid ?: "unknown_user"
        val finalClothingType = "${clothingType.toLowerCase()}-${selectedGender?.toLowerCase()}"

        val intent = Intent(this, ResultActivity::class.java).apply {
            putExtra("IMAGE_PATH", croppedImageUri.path)
            putExtra("CLOTHING_TYPE", finalClothingType)
            putExtra("UID", uid)
        }
        startActivity(intent)
    }
}
