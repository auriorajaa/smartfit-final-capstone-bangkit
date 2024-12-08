package com.example.smartfit.view.setting.account

import android.graphics.drawable.AnimationDrawable
import android.os.Bundle
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import com.example.smartfit.R

class AccountActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_account)

        // Mengatur background bergerak
        val constraintLayout: ConstraintLayout = findViewById(R.id.main)
        val animationDrawable = constraintLayout.background as AnimationDrawable
        animationDrawable.setEnterFadeDuration(1500)
        animationDrawable.setExitFadeDuration(3000)
        animationDrawable.start()

        val backButton = findViewById<androidx.cardview.widget.CardView>(R.id.btn_back_account)
        backButton.setOnClickListener {
            finish()
        }
    }
}