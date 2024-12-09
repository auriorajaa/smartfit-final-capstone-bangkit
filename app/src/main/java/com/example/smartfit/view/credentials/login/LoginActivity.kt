package com.example.smartfit.view.credentials.login

import android.content.Intent
import android.graphics.drawable.AnimationDrawable
import android.os.Bundle
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import com.example.smartfit.R
import com.example.smartfit.databinding.ActivityLoginBinding
import com.example.smartfit.view.MainActivity
import com.example.smartfit.view.credentials.customview.EmailInputView
import com.example.smartfit.view.credentials.customview.PasswordInputView
import com.example.smartfit.view.credentials.forgotpassword.ForgotPasswordActivity
import com.example.smartfit.view.credentials.register.RegisterActivity
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInAccount
import com.google.android.gms.auth.api.signin.GoogleSignInClient
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.gms.common.api.ApiException
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseAuthInvalidUserException
import com.google.firebase.auth.FirebaseAuthInvalidCredentialsException
import com.google.firebase.auth.GoogleAuthProvider
import com.google.firebase.database.FirebaseDatabase

class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding
    private lateinit var auth: FirebaseAuth
    private lateinit var database: FirebaseDatabase
    private lateinit var googleSignInClient: GoogleSignInClient
    private val RC_SIGN_IN = 9001

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Konfigurasi Firebase Auth dan Realtime Database
        auth = FirebaseAuth.getInstance()
        database = FirebaseDatabase.getInstance()

        // Konfigurasi Google Sign-In
        val gso = GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
            .requestIdToken(getString(R.string.default_web_client_id))
            .requestEmail()
            .build()

        googleSignInClient = GoogleSignIn.getClient(this, gso)

        // Mengatur background animasi
        val constraintLayout: ConstraintLayout = binding.mainLogin
        val animationDrawable = constraintLayout.background as AnimationDrawable
        animationDrawable.setEnterFadeDuration(1500)
        animationDrawable.setExitFadeDuration(3000)
        animationDrawable.start()

        binding.btnSignInGoogle.setOnClickListener {
            signInWithGoogle()
        }

        binding.btnSignIn.setOnClickListener {
            if (validateInputs()) {
                val email = binding.emailInput.getText()
                val password = binding.passwordInput.getText()
                loginUser(email, password)
            }
        }

        binding.tvSignup.setOnClickListener {
            startActivity(Intent(this, RegisterActivity::class.java))
        }

        binding.tvForgotPassword.setOnClickListener {
            startActivity(Intent(this, ForgotPasswordActivity::class.java))
        }
    }

    private fun validateInputs(): Boolean {
        val isEmailValid = binding.emailInput.isEmailValid()
        val isPasswordValid = binding.passwordInput.isPasswordValid()

        if (!isEmailValid) {
            showAlertDialog("Input Error", "Please enter a valid email address.", false)
        } else if (!isPasswordValid) {
            showAlertDialog("Input Error", "Password must be 6 characters long.", false)
        }

        return isEmailValid && isPasswordValid
    }

    private fun signInWithGoogle() {
        val signInIntent = googleSignInClient.signInIntent
        startActivityForResult(signInIntent, RC_SIGN_IN)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)

        if (requestCode == RC_SIGN_IN) {
            val task = GoogleSignIn.getSignedInAccountFromIntent(data)
            try {
                val account = task.getResult(ApiException::class.java)!!
                firebaseAuthWithGoogle(account)
            } catch (e: ApiException) {
                showAlertDialog("Google sign in failed", e.message ?: "Unknown error occurred.", false)
            }
        }
    }

    private fun firebaseAuthWithGoogle(account: GoogleSignInAccount) {
        val credential = GoogleAuthProvider.getCredential(account.idToken, null)
        auth.signInWithCredential(credential)
            .addOnCompleteListener(this) { task ->
                if (task.isSuccessful) {
                    val user = auth.currentUser
                    user?.let {
                        val userRef = database.reference.child("users").child(it.uid)
                        val userData = mapOf(
                            "email" to it.email,
                            "displayName" to (account.displayName ?: ""),
                            "photoURL" to (account.photoUrl?.toString() ?: ""),
                            "provider" to "google",
                            "lastLogin" to System.currentTimeMillis()
                        )
                        userRef.setValue(userData)
                            .addOnCompleteListener { dbTask ->
                                if (dbTask.isSuccessful) {
                                    navigateToMain()
                                } else {
                                    showAlertDialog("Database Error", dbTask.exception?.message ?: "Unknown error.", false)
                                }
                            }
                    }
                } else {
                    showAlertDialog("Authentication Failed", task.exception?.message ?: "Unknown error.", false)
                }
            }
    }

    private fun loginUser(email: String, password: String) {
        auth.signInWithEmailAndPassword(email, password)
            .addOnCompleteListener(this) { task ->
                if (task.isSuccessful) {
                    val user = auth.currentUser
                    if (user != null && user.isEmailVerified) {
                        navigateToMain()
                    } else {
                        showAlertDialog("Email Not Verified", "Please verify your email before logging in.", false)
                        auth.signOut()
                    }
                } else {
                    val message = when (task.exception) {
                        is FirebaseAuthInvalidUserException, is FirebaseAuthInvalidCredentialsException -> "Invalid email or password."
                        else -> task.exception?.message ?: "Unknown error."
                    }
                    showAlertDialog("Login Failed", message, false)
                }
            }
    }

    private fun showAlertDialog(title: String, message: String, isSuccess: Boolean) {
        AlertDialog.Builder(this)
            .setTitle(title)
            .setMessage(message)
            .setPositiveButton("OK") { dialog, _ ->
                dialog.dismiss()
                if (isSuccess) navigateToMain()
            }
            .show()
    }

    private fun navigateToMain() {
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }
}
