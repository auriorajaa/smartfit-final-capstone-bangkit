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
            checkIfEmailExists(email, password)
        }
    }

    private fun checkIfEmailExists(email: String, password: String) {
        auth.fetchSignInMethodsForEmail(email)
            .addOnCompleteListener { task ->
                if (task.isSuccessful) {
                    val signInMethods = task.result?.signInMethods
                    if (!signInMethods.isNullOrEmpty()) {
                        // Email sudah terdaftar di Firebase Authentication
                        showEmailExistsDialog(email)
                    } else {
                        // Email belum terdaftar di Firebase Authentication
                        checkEmailInDatabase(email, password)
                    }
                } else {
                    // Gagal melakukan pengecekan email di Firebase Authentication
                    showAlertDialog("Error", task.exception?.message ?: "Unknown error occurred while checking email.", false)
                }
            }
    }

    private fun checkEmailInDatabase(email: String, password: String) {
        // Cek apakah email sudah terdaftar di Firebase Realtime Database
        database.reference.child("users").orderByChild("email").equalTo(email).get()
            .addOnCompleteListener { task ->
                if (task.isSuccessful) {
                    val dataSnapshot = task.result
                    if (dataSnapshot.exists()) {
                        // Email sudah terdaftar di Firebase Realtime Database
                        showEmailExistsDialog(email)
                    } else {
                        // Email belum terdaftar, lanjutkan dengan proses registrasi
                        registerUser(email, password)
                    }
                } else {
                    // Gagal melakukan pengecekan email di Firebase Realtime Database
                    showAlertDialog("Error", task.exception?.message ?: "Unknown error occurred while checking email.", false)
                }
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
                                    // Kirim email verifikasi
                                    user.sendEmailVerification()
                                        .addOnCompleteListener { verifyTask ->
                                            if (verifyTask.isSuccessful) {
                                                showAlertDialog(
                                                    "Registration Successful",
                                                    "A verification email has been sent to your email address. Please verify your email before logging in.",
                                                    true
                                                )
                                            } else {
                                                showAlertDialog(
                                                    "Verification Email Failed",
                                                    verifyTask.exception?.message
                                                        ?: "Unknown error occurred.",
                                                    false
                                                )
                                            }
                                        }
                                } else {
                                    showAlertDialog(
                                        "Database Error",
                                        dbTask.exception?.message ?: "Unknown error occurred.",
                                        false
                                    )
                                }
                            }
                    }
                } else {
                    showAlertDialog(
                        "Registration Failed",
                        task.exception?.message ?: "Unknown error occurred.",
                        false
                    )
                }
            }
    }

    private fun showEmailExistsDialog(email: String) {
        val builder = AlertDialog.Builder(this)
        builder.setTitle("Email Already Registered")
        builder.setMessage("The email address $email is already registered. Please login or use a different email address.")
        builder.setPositiveButton("Login") { dialog, _ ->
            dialog.dismiss()
            navigateToLogin()
        }
        builder.setNegativeButton("Try Again") { dialog, _ ->
            dialog.dismiss()
        }
        val dialog = builder.create()
        dialog.show()
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
