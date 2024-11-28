package com.example.smartfit

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.example.smartfit.databinding.ActivityLoginBinding
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
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        auth = FirebaseAuth.getInstance()
        database = FirebaseDatabase.getInstance()

        // Konfigurasi Google Sign-In
        val gso = GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
            .requestIdToken(getString(R.string.default_web_client_id))
            .requestEmail()
            .build()

        googleSignInClient = GoogleSignIn.getClient(this, gso)

        binding.googleSignInButton.setOnClickListener {
            signInWithGoogle()
        }

        binding.loginButton.setOnClickListener {
            val email = binding.emailEditText.text.toString().trim()
            val password = binding.passwordEditText.text.toString().trim()
            if (email.isEmpty() || password.isEmpty()) {
                showAlertDialog("Input Error", "Email and password are required.", false)
            } else {
                loginUser(email, password)
            }
        }

        binding.registerButton.setOnClickListener {
            val intent = Intent(this, RegisterActivity::class.java)
            startActivity(intent)
        }

        binding.forgotPasswordButton.setOnClickListener {
            val intent = Intent(this, ForgotPasswordActivity::class.java)
            startActivity(intent)
        }
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
                    // Login atau registrasi berhasil
                    val user = auth.currentUser
                    user?.let {
                        val uid = it.uid
                        val email = it.email
                        val currentTime = System.currentTimeMillis()
                        val userRef = database.reference.child("users").child(uid)

                        val userData = mapOf(
                            "email" to email,
                            "createdAt" to currentTime,
                            "displayName" to (account.displayName ?: ""),
                            "isNewUser" to false,
                            "lastLogin" to currentTime,
                            "photoURL" to (account.photoUrl?.toString() ?: ""),
                            "provider" to "google",
                            "updatedAt" to currentTime
                        )

                        userRef.setValue(userData).addOnCompleteListener { dbTask ->
                            if (dbTask.isSuccessful) {
                                showAlertDialog("Login Successful", "Welcome!", true)
                            } else {
                                showAlertDialog("Database Error", dbTask.exception?.message ?: "Unknown error occurred.", false)
                            }
                        }
                    }
                } else {
                    showAlertDialog("Authentication failed", task.exception?.message ?: "Unknown error occurred.", false)
                }
            }
    }


    private fun loginUser(email: String, password: String) {
        auth.signInWithEmailAndPassword(email, password)
            .addOnCompleteListener(this) { task ->
                if (task.isSuccessful) {
                    val user = auth.currentUser
                    if (user != null && user.isEmailVerified) {
                        showAlertDialog("Login Successful", "Welcome!", true)
                    } else {
                        showAlertDialog("Email Not Verified", "Please verify your email address before logging in. Check your email for the verification link.", false)
                        auth.signOut() // Sign out user to prevent access
                    }
                } else {
                    val message = when (task.exception) {
                        is FirebaseAuthInvalidUserException, is FirebaseAuthInvalidCredentialsException -> "Email or password is incorrect, please check and try again."
                        else -> task.exception?.message ?: "Unknown error occurred."
                    }
                    showAlertDialog("Login Failed", message, false)
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
                navigateToMain()
            }
        }
        val dialog = builder.create()
        dialog.show()
    }

    private fun navigateToMain() {
        val intent = Intent(this, MainActivity::class.java)
        startActivity(intent)
        finish()
    }
}
