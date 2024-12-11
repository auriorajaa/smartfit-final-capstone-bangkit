package com.example.smartfit.view.credentials.forgotpassword

import android.content.Intent
import android.graphics.Color
import android.graphics.drawable.AnimationDrawable
import android.os.Build
import android.os.Bundle
import android.view.View
import android.view.WindowInsetsController
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import com.example.smartfit.R
import com.example.smartfit.databinding.ActivityForgotPasswordBinding
import com.example.smartfit.utils.showUniversalDialog
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

        // Mengatur background bergerak
        val constraintLayout: ConstraintLayout = findViewById(R.id.main)
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

        auth = FirebaseAuth.getInstance()
        database = FirebaseDatabase.getInstance()

        binding.btnResetPassword.setOnClickListener {
            val email = binding.etForgotPassword.text.toString().trim()
            if (email.isEmpty()) {
                showUniversalDialog(
                    context = this,
                    title = getString(R.string.input_error_title),
                    message = getString(R.string.email_empty_message),
                    positiveButtonText = getString(R.string.ok_button),
                    negativeButtonText = null,
                    positiveAction = null,
                    negativeAction = null
                )
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
                    showUniversalDialog(
                        context = this,
                        title = getString(R.string.error_title),
                        message = getString(R.string.email_not_registered_message),
                        positiveButtonText = getString(R.string.ok_button),
                        negativeButtonText = null,
                        positiveAction = null,
                        negativeAction = null
                    )
                }
            }
            .addOnFailureListener {
                showUniversalDialog(
                    context = this,
                    title = getString(R.string.error_title),
                    message = getString(R.string.database_access_error_message),
                    positiveButtonText = getString(R.string.ok_button),
                    negativeButtonText = null,
                    positiveAction = null,
                    negativeAction = null
                )
            }
    }

    private fun sendPasswordResetEmail(email: String) {
        auth.sendPasswordResetEmail(email)
            .addOnCompleteListener(this) { task ->
                if (task.isSuccessful) {
                    showUniversalDialog(
                        context = this,
                        title = getString(R.string.reset_password_title),
                        message = getString(R.string.reset_password_success_message),
                        positiveButtonText = getString(R.string.ok_button),
                        negativeButtonText = null,
                        positiveAction = { navigateToLogin() },
                        negativeAction = null
                    )
                } else {
                    val message = when (task.exception) {
                        is FirebaseAuthInvalidUserException -> getString(R.string.email_not_registered_message)
                        else -> task.exception?.message ?: getString(R.string.unknown_error_message)
                    }
                    showUniversalDialog(
                        context = this,
                        title = getString(R.string.reset_password_failed_title),
                        message = message,
                        positiveButtonText = getString(R.string.ok_button),
                        negativeButtonText = null,
                        positiveAction = null,
                        negativeAction = null
                    )
                }
            }
    }

    private fun navigateToLogin() {
        val intent = Intent(this, LoginActivity::class.java)
        startActivity(intent)
        finish()
    }
}
