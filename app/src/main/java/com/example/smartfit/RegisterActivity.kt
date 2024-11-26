package com.example.smartfit

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.example.smartfit.databinding.ActivityRegisterBinding
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.database.FirebaseDatabase

class RegisterActivity : AppCompatActivity() {

    private lateinit var binding: ActivityRegisterBinding
    private lateinit var auth: FirebaseAuth
    private lateinit var database: FirebaseDatabase

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityRegisterBinding.inflate(layoutInflater)
        setContentView(binding.root)

        auth = FirebaseAuth.getInstance()
        database = FirebaseDatabase.getInstance()

        binding.registerButton.setOnClickListener {
            val email = binding.emailEditText.text.toString()
            val password = binding.passwordEditText.text.toString()
            registerUser(email, password)
        }
    }

    private fun registerUser(email: String, password: String) {
        auth.createUserWithEmailAndPassword(email, password)
            .addOnCompleteListener(this) { task ->
                if (task.isSuccessful) {
                    val user = auth.currentUser
                    user?.let {
                        val uid = it.uid
                        val userEmail = it.email
                        val currentTime = System.currentTimeMillis()

                        // Simpan data pengguna di Realtime Database
                        val userRef = database.reference.child("users").child(uid)
                        val userData = mapOf(
                            "email" to userEmail,
                            "createdAt" to currentTime,
                            "displayName" to "",
                            "isNewUser" to false,
                            "lastLogin" to currentTime,
                            "photoURL" to "",
                            "provider" to "password",
                            "updatedAt" to currentTime
                        )

                        userRef.setValue(userData)
                            .addOnCompleteListener { dbTask ->
                                if (dbTask.isSuccessful) {
                                    showAlertDialog("Registration Successful", "Your account has been created successfully.", true)
                                } else {
                                    // Tangani error penyimpanan di Realtime Database
                                    showAlertDialog("Database Error", dbTask.exception?.message ?: "Unknown error occurred.", false)
                                }
                            }
                    }
                } else {
                    // Tangani error registrasi
                    showAlertDialog("Registration Failed", task.exception?.message ?: "Unknown error occurred.", false)
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
