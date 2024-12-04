package com.example.smartfit.view.setting

import android.content.Intent
import android.os.Bundle
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import com.example.smartfit.R
import com.example.smartfit.view.setting.account.AccountActivity

class SettingActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_setting)

        val backButton = findViewById<androidx.cardview.widget.CardView>(R.id.btn_back_setting)
        backButton.setOnClickListener {
            finish()
        }

        val logoutButton = findViewById<com.google.android.material.card.MaterialCardView>(R.id.cv_logout)
        logoutButton.setOnClickListener {
            finish()
        }

        val accountButton = findViewById<com.google.android.material.card.MaterialCardView>(R.id.cv_account)
        accountButton.setOnClickListener {
            val intent = Intent(this, AccountActivity::class.java)
            startActivity(intent)
        }
    }
}