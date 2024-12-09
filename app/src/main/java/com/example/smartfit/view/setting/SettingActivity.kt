package com.example.smartfit.view.setting

import android.content.Intent
import android.graphics.drawable.AnimationDrawable
import android.os.Bundle
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import com.example.smartfit.R
import com.example.smartfit.view.credentials.login.LoginActivity
import com.example.smartfit.view.setting.account.AccountActivity
import com.google.android.material.card.MaterialCardView
import com.google.firebase.auth.FirebaseAuth

class SettingActivity : AppCompatActivity() {

    private lateinit var auth: FirebaseAuth

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_setting)


        // Inisialisasi FirebaseAuth
        auth = FirebaseAuth.getInstance()

        // Mengatur background bergerak
        val constraintLayout: ConstraintLayout = findViewById(R.id.main)
        val animationDrawable = constraintLayout.background as AnimationDrawable
        animationDrawable.setEnterFadeDuration(1500)
        animationDrawable.setExitFadeDuration(3000)
        animationDrawable.start()

        val backButton = findViewById<androidx.cardview.widget.CardView>(R.id.btn_back_setting)
        backButton.setOnClickListener {
            finish()
        }

        // Tombol logout
        val logoutButton = findViewById<MaterialCardView>(R.id.cv_logout)
        logoutButton.setOnClickListener {
            performLogout()
        }

        val accountButton = findViewById<com.google.android.material.card.MaterialCardView>(R.id.cv_account)
        accountButton.setOnClickListener {
            val intent = Intent(this, AccountActivity::class.java)
            startActivity(intent)
        }
    }

    private fun performLogout() {
        auth.signOut() // Logout dari Firebase Authentication
        Toast.makeText(this, "You have successfully logged out.", Toast.LENGTH_SHORT).show()

        // Arahkan pengguna kembali ke LoginActivity
        val intent = Intent(this, LoginActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK // Membersihkan back stack
        startActivity(intent)
    }
}