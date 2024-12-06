package com.example.smartfit.view.detection.camera

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import com.example.smartfit.R
import com.example.smartfit.view.detection.camera2.Camera2Activity

class CameraActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_camera)

        val backButton = findViewById<androidx.cardview.widget.CardView>(R.id.btn_back_camera)
        backButton.setOnClickListener {
            finish()
        }

        val btnCamera = findViewById<Button>(R.id.btn_open_camera)
        btnCamera.setOnClickListener {
            val intent = Intent(this, Camera2Activity::class.java)
            startActivity(intent)
        }
    }
}