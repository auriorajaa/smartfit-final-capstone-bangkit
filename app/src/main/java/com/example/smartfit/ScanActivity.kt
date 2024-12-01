package com.example.smartfit

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import com.example.smartfit.databinding.ActivityScanBinding
import com.google.firebase.auth.FirebaseAuth

class ScanActivity : AppCompatActivity() {

    private lateinit var binding: ActivityScanBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityScanBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val croppedImageUriString = intent.getStringExtra("CROPPED_IMAGE_URI")
        val croppedImageUri = Uri.parse(croppedImageUriString)
        binding.scannedImageView.setImageURI(croppedImageUri)

        binding.scanButton.setOnClickListener {
            binding.scanButton.visibility = View.GONE
            binding.retakeButton.visibility = View.GONE
            binding.buttonContainer.visibility = View.VISIBLE
        }

        binding.retakeButton.setOnClickListener {
            val intent = Intent(this, ChooseActivity::class.java)
            startActivity(intent)
        }

        binding.streetWearButton.setOnClickListener {
            processImage(croppedImageUri, "streetwear")
        }

        binding.pajamasButton.setOnClickListener {
            processImage(croppedImageUri, "pajamas")
        }

        binding.weddingButton.setOnClickListener {
            processImage(croppedImageUri, "wedding")
        }

        binding.formalButton.setOnClickListener {
            processImage(croppedImageUri, "formal")
        }
    }

    private fun processImage(imageUri: Uri, clothingType: String) {
        val user = FirebaseAuth.getInstance().currentUser
        val uid = user?.uid ?: "unknown_user"

        val intent = Intent(this, ResultActivity::class.java).apply {
            putExtra("IMAGE_PATH", imageUri.path)
            putExtra("CLOTHING_TYPE", clothingType)
            putExtra("UID", uid)
        }
        startActivity(intent)
    }
}
