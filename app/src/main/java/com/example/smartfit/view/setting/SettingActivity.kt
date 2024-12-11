package com.example.smartfit.view.setting

import android.content.Intent
import android.graphics.drawable.AnimationDrawable
import android.os.Bundle
import android.provider.Settings
import android.widget.TextView
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import com.example.smartfit.R
import com.example.smartfit.databinding.ActivitySettingBinding
import com.example.smartfit.view.credentials.login.LoginActivity
import com.example.smartfit.view.setting.account.AccountActivity
import com.google.android.material.button.MaterialButton
import com.google.android.material.card.MaterialCardView
import com.google.firebase.auth.FirebaseAuth

class SettingActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySettingBinding
    private lateinit var auth: FirebaseAuth

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        // Inisialisasi binding dengan inflate layout
        binding = ActivitySettingBinding.inflate(layoutInflater)
        setContentView(binding.root) // Gunakan binding.root di sini

        // Inisialisasi FirebaseAuth
        auth = FirebaseAuth.getInstance()

        // Open Locale Settings when the ImageView is clicked
        binding.cvLanguage.setOnClickListener {
            startActivity(Intent(Settings.ACTION_LOCALE_SETTINGS))
        }

        // Mengatur background bergerak
        val constraintLayout: ConstraintLayout = findViewById(R.id.main)
        val animationDrawable = constraintLayout.background as AnimationDrawable
        animationDrawable.setEnterFadeDuration(1500)
        animationDrawable.setExitFadeDuration(3000)
        animationDrawable.start()

        val backButton = findViewById<MaterialCardView>(R.id.btn_back_setting)
        backButton.setOnClickListener {
            finish()
        }

        // Tombol logout
        val logoutButton = findViewById<MaterialCardView>(R.id.cv_logout)
        logoutButton.setOnClickListener {
            showLogoutConfirmationDialog()
        }

        val accountButton = findViewById<MaterialCardView>(R.id.cv_account)
        accountButton.setOnClickListener {
            val intent = Intent(this, AccountActivity::class.java)
            startActivity(intent)
        }
    }

    private fun showLogoutConfirmationDialog() {
        val dialogView = layoutInflater.inflate(R.layout.custom_dialog_layout, null)
        val builder = AlertDialog.Builder(this)
        builder.setView(dialogView)

        val dialog = builder.create()

        dialogView.findViewById<TextView>(R.id.dialog_title).text = getString(R.string.title_logout)
        dialogView.findViewById<TextView>(R.id.dialog_message).text = getString(R.string.logout_message)

        val positiveButton = dialogView.findViewById<MaterialButton>(R.id.dialog_positive_button)
        val negativeButton = dialogView.findViewById<MaterialButton>(R.id.dialog_negative_button)

        positiveButton.setOnClickListener {
            dialog.dismiss()
            performLogout()
        }

        negativeButton.setOnClickListener {
            dialog.dismiss()
        }

        dialog.show()
    }


    private fun performLogout() {
        auth.signOut() // Logout dari Firebase Authentication
        Toast.makeText(this, getString(R.string.success_logout), Toast.LENGTH_SHORT).show()

        // Arahkan pengguna kembali ke LoginActivity
        val intent = Intent(this, LoginActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK // Membersihkan back stack
        startActivity(intent)
    }
}
