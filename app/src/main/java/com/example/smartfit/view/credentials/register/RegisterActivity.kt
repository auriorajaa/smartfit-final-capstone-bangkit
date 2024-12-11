package com.example.smartfit.view.credentials.register

import android.content.Intent
import android.graphics.drawable.AnimationDrawable
import android.os.Bundle
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import com.example.smartfit.R
import com.example.smartfit.databinding.ActivityRegisterBinding
import com.example.smartfit.view.credentials.customview.EmailInputView
import com.example.smartfit.view.credentials.customview.NameInputView
import com.example.smartfit.view.credentials.customview.PasswordInputView
import com.example.smartfit.view.credentials.login.LoginActivity
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.database.FirebaseDatabase

class RegisterActivity : AppCompatActivity() {

    private lateinit var binding: ActivityRegisterBinding
    private lateinit var auth: FirebaseAuth
    private lateinit var database: FirebaseDatabase

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        binding = ActivityRegisterBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Mengatur background bergerak
        val constraintLayout: ConstraintLayout = findViewById(R.id.main)
        val animationDrawable = constraintLayout.background as AnimationDrawable
        animationDrawable.setEnterFadeDuration(1500)
        animationDrawable.setExitFadeDuration(3000)
        animationDrawable.start()

        // Inisialisasi Firebase
        auth = FirebaseAuth.getInstance()
        database = FirebaseDatabase.getInstance()

        // Tombol register
        binding.btnSignUp.setOnClickListener {
            if (validateInputs()) {
                val email = binding.emailInputView.getText()
                val password = binding.passwordInputView.binding.passwordEditText.text.toString()
                checkIfEmailExists(email, password)
            }
        }

        binding.tvSignin.setOnClickListener {
            val intent = Intent(this, LoginActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
            startActivity(intent)
        }
    }

    private fun validateInputs(): Boolean {
        val nameInput = findViewById<NameInputView>(R.id.nameInput)
        val emailInput = findViewById<EmailInputView>(R.id.emailInputView)
        val passwordInput = findViewById<PasswordInputView>(R.id.passwordInputView)

        val isNameValid = nameInput.isNameValid()
        val isEmailValid = emailInput.isEmailValid()
        val isPasswordValid = passwordInput.isPasswordValid()

        return isNameValid && isEmailValid && isPasswordValid
    }

    private fun checkIfEmailExists(email: String, password: String) {
        auth.fetchSignInMethodsForEmail(email)
            .addOnCompleteListener { task ->
                if (task.isSuccessful) {
                    val signInMethods = task.result?.signInMethods
                    if (!signInMethods.isNullOrEmpty()) {
                        showEmailExistsDialog(email)
                    } else {
                        checkEmailInDatabase(email, password)
                    }
                } else {
                    showAlertDialog("Error", task.exception?.message ?: "Unknown error occurred while checking email.", false)
                }
            }
    }

    private fun checkEmailInDatabase(email: String, password: String) {
        database.reference.child("users").orderByChild("email").equalTo(email).get()
            .addOnCompleteListener { task ->
                if (task.isSuccessful) {
                    val dataSnapshot = task.result
                    if (dataSnapshot.exists()) {
                        showEmailExistsDialog(email)
                    } else {
                        registerUser(email, password)
                    }
                } else {
                    showAlertDialog("Error", task.exception?.message ?: "Unknown error occurred while checking email.", false)
                }
            }
    }

    private fun registerUser(email: String, password: String) {
        val name = binding.nameInput.binding.nameEditText.text.toString()
        auth.createUserWithEmailAndPassword(email, password)
            .addOnCompleteListener(this) { task ->
                if (task.isSuccessful) {
                    val user = auth.currentUser
                    user?.let {
                        val uid = it.uid
                        val currentTime = System.currentTimeMillis()
                        val userRef = database.reference.child("users").child(uid)
                        val userData = mapOf(
                            "email" to email,
                            "createdAt" to currentTime,
                            "displayName" to name,
                            "isNewUser" to false,
                            "lastLogin" to currentTime,
                            "photoURL" to "",
                            "provider" to "password",
                            "updatedAt" to currentTime
                        )

                        userRef.setValue(userData)
                            .addOnCompleteListener { dbTask ->
                                if (dbTask.isSuccessful) {
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
                                                    verifyTask.exception?.message ?: "Unknown error occurred.",
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
        builder.create().show()
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
        builder.create().show()
    }

    private fun navigateToLogin() {
        val intent = Intent(this, LoginActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
        startActivity(intent)
        finish()
    }
}
