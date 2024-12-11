package com.example.smartfit.view.credentials.forgotpassword

import android.content.Intent
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.view.View
import android.view.WindowInsetsController
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.example.smartfit.databinding.ActivityForgotPasswordBinding
import com.example.smartfit.view.credentials.login.LoginActivity
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseAuthInvalidUserException
import com.google.firebase.database.FirebaseDatabase

class ForgotPasswordActivity : AppCompatActivity() {

    private lateinit var binding: ActivityForgotPasswordBinding
    private lateinit var auth: FirebaseAuth
    private lateinit var database: FirebaseDatabase

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityForgotPasswordBinding.inflate(layoutInflater)
        setContentView(binding.root)

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

        auth = FirebaseAuth.getInstance()
        database = FirebaseDatabase.getInstance()

        binding.btnResetPassword.setOnClickListener {
            val email = binding.etForgotPassword.text.toString().trim()
            if (email.isEmpty()) {
                showAlertDialog("Input Error", "Please enter your email address.", false)
            } else {
                checkEmailAndSendReset(email)
            }
        }
    }

    private fun checkEmailAndSendReset(email: String) {
        database.reference.child("users").orderByChild("email").equalTo(email).get()
            .addOnSuccessListener { dataSnapshot ->
                if (dataSnapshot.exists()) {
                    sendPasswordResetEmail(email)
                } else {
                    showAlertDialog("Error", "Email address is not registered.", false)
                }
            }
            .addOnFailureListener {
                showAlertDialog(
                    "Error",
                    "Failed to access database. Please try again later.",
                    false
                )
            }
    }

    private fun sendPasswordResetEmail(email: String) {
        auth.sendPasswordResetEmail(email)
            .addOnCompleteListener(this) { task ->
                if (task.isSuccessful) {
                    showAlertDialog(
                        "Reset Password",
                        "A password reset link has been sent to your email.",
                        true
                    )
                } else {
                    val message = when (task.exception) {
                        is FirebaseAuthInvalidUserException -> "Email address is not registered."
                        else -> task.exception?.message ?: "Unknown error occurred."
                    }
                    showAlertDialog("Reset Password Failed", message, false)
                }
            }
    }

    private fun showAlertDialog(title: String, message: String, isSuccess: Boolean) {
        val builder = AlertDialog.Builder(this)
        builder.setTitle(title)
        builder.setMessage(message)
        builder.setPositiveButton("OK") { dialog, _ ->
            dialog.dismiss()
            if (isSuccess) {
                navigateToLogin()
            }
        }
        val dialog = builder.create()
        dialog.show()
    }

    private fun navigateToLogin() {
        val intent = Intent(this, LoginActivity::class.java)
        startActivity(intent)
        finish()
    }
}
