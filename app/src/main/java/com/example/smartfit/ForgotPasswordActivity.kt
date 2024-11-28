package com.example.smartfit

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.example.smartfit.databinding.ActivityForgotPasswordBinding
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

        auth = FirebaseAuth.getInstance()
        database = FirebaseDatabase.getInstance()

        binding.resetPasswordButton.setOnClickListener {
            val email = binding.emailEditText.text.toString().trim()
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
