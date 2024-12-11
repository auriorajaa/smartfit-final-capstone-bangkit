package com.example.smartfit.view.credentials.register

import android.content.Intent
import android.graphics.drawable.AnimationDrawable
import android.os.Bundle
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import com.example.smartfit.R
import com.example.smartfit.databinding.ActivityRegisterBinding
import com.example.smartfit.utils.showUniversalDialog
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
                    showUniversalDialog(
                        context = this,
                        title = "Error",
                        message = task.exception?.message ?: "Unknown error occurred while checking email.",
                        positiveButtonText = getString(R.string.ok),
                        negativeButtonText = null,
                        positiveAction = null,
                        negativeAction = null
                    )
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
                    showUniversalDialog(
                        context = this,
                        title = "Error",
                        message = task.exception?.message ?: "Unknown error occurred while checking email.",
                        positiveButtonText = getString(R.string.ok),
                        negativeButtonText = null,
                        positiveAction = null,
                        negativeAction = null
                    )
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
                                                showUniversalDialog(
                                                    context = this,
                                                    title = getString(R.string.registration_successful_title),
                                                    message = getString(R.string.registration_successful_message),
                                                    positiveButtonText = getString(R.string.ok),
                                                    negativeButtonText = null,
                                                    positiveAction = { navigateToLogin() },
                                                    negativeAction = null
                                                )
                                            } else {
                                                showUniversalDialog(
                                                    context = this,
                                                    title = getString(R.string.verification_email_failed_title),
                                                    message = verifyTask.exception?.message ?: getString(R.string.verification_email_failed_message),
                                                    positiveButtonText = getString(R.string.ok),
                                                    negativeButtonText = null,
                                                    positiveAction = null,
                                                    negativeAction = null
                                                )
                                            }
                                        }
                                } else {
                                    showUniversalDialog(
                                        context = this,
                                        title = getString(R.string.database_error_title),
                                        message = dbTask.exception?.message ?: getString(R.string.database_error_message),
                                        positiveButtonText = getString(R.string.ok),
                                        negativeButtonText = null,
                                        positiveAction = null,
                                        negativeAction = null
                                    )
                                }
                            }
                    }
                } else {
                    showUniversalDialog(
                        context = this,
                        title = getString(R.string.registration_failed_title),
                        message = task.exception?.message ?: getString(R.string.registration_failed_message),
                        positiveButtonText = getString(R.string.ok),
                        negativeButtonText = null,
                        positiveAction = null,
                        negativeAction = null
                    )
                }
            }
    }

    private fun showEmailExistsDialog(email: String) {
        showUniversalDialog(
            context = this,
            title = getString(R.string.email_exists_title),
            message = getString(R.string.email_exists_message, email),
            positiveButtonText = getString(R.string.login_button),
            negativeButtonText = getString(R.string.try_again_button),
            positiveAction = { navigateToLogin() },
            negativeAction = null
        )
    }

    private fun showUniversalDialog(title: String, message: String, isSuccess: Boolean) {
        showUniversalDialog(
            context = this,
            title = title,
            message = message,
            positiveButtonText = getString(R.string.ok),
            negativeButtonText = null,
            positiveAction = { if (isSuccess) navigateToLogin() },
            negativeAction = null
        )
    }

    private fun navigateToLogin() {
        val intent = Intent(this, LoginActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
        startActivity(intent)
        finish()
    }
}
