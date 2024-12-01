package com.example.smartfit

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import com.example.smartfit.databinding.ActivityCategoryBinding
import com.google.firebase.auth.FirebaseAuth

class CategoryActivity : AppCompatActivity() {

    private lateinit var binding: ActivityCategoryBinding
    private var selectedGender: String? = null
    private lateinit var croppedImageUri: Uri

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityCategoryBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val croppedImageUriString = intent.getStringExtra("CROPPED_IMAGE_URI")
        croppedImageUri = Uri.parse(croppedImageUriString)

        binding.menButton.setOnClickListener {
            selectedGender = "men"
            binding.clothingTypeContainer.visibility = View.VISIBLE
        }

        binding.womenButton.setOnClickListener {
            selectedGender = "women"
            binding.clothingTypeContainer.visibility = View.VISIBLE
        }

        binding.formalButton.setOnClickListener {
            proceedToResult("formal")
        }

        binding.weddingButton.setOnClickListener {
            proceedToResult("wedding")
        }

        binding.streetWearButton.setOnClickListener {
            proceedToResult("streetwear")
        }

        binding.pajamasButton.setOnClickListener {
            proceedToResult("pajamas")
        }

        binding.vintageButton.setOnClickListener {
            proceedToResult("vintage")
        }

        binding.casualButton.setOnClickListener {
            proceedToResult("casual")
        }

        binding.sportswearButton.setOnClickListener {
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
