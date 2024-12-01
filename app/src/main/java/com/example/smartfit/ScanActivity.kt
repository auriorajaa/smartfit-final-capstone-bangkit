package com.example.smartfit

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.example.smartfit.databinding.ActivityScanBinding

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
            val intent = Intent(this, CategoryActivity::class.java).apply {
                putExtra("CROPPED_IMAGE_URI", croppedImageUri.toString())
            }
            startActivity(intent)
        }

        binding.retakeButton.setOnClickListener {
            val intent = Intent(this, ChooseActivity::class.java)
            startActivity(intent)
        }
    }
}
