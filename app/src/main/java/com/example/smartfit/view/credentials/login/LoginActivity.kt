package com.example.smartfit.view.credentials.login

import android.content.Intent
import android.graphics.drawable.AnimationDrawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.example.smartfit.R
import com.example.smartfit.databinding.ActivityLoginBinding
import com.example.smartfit.utils.showUniversalDialog
import com.example.smartfit.view.MainActivity
import com.example.smartfit.view.credentials.forgotpassword.ForgotPasswordActivity
import com.example.smartfit.view.credentials.register.RegisterActivity
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInAccount
import com.google.android.gms.auth.api.signin.GoogleSignInClient
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.gms.common.api.ApiException
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseAuthInvalidCredentialsException
import com.google.firebase.auth.FirebaseAuthInvalidUserException
import com.google.firebase.auth.GoogleAuthProvider
import com.google.firebase.database.FirebaseDatabase

class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding
    private lateinit var auth: FirebaseAuth
    private lateinit var database: FirebaseDatabase
    private lateinit var googleSignInClient: GoogleSignInClient
    private val RC_SIGN_IN = 9001
    private val hideHandler = Handler(Looper.getMainLooper())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Menyembunyikan tombol navigasi saja
        val controller = ViewCompat.getWindowInsetsController(window.decorView)
        controller?.hide(WindowInsetsCompat.Type.navigationBars())
        controller?.systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_DEFAULT

        window.decorView.setOnSystemUiVisibilityChangeListener {
            hideHandler.postDelayed({
                controller?.hide(WindowInsetsCompat.Type.navigationBars())
            }, 5000)
        }

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
            val intent = Intent(this, RegisterActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
            startActivity(intent)
        }

        binding.tvForgotPassword.setOnClickListener {
            startActivity(Intent(this, ForgotPasswordActivity::class.java))
        }
    }

    private fun validateInputs(): Boolean {
        val isEmailValid = binding.emailInput.isEmailValid()
        val isPasswordValid = binding.passwordInput.isPasswordValid()

        if (!isEmailValid) {
            showUniversalDialog(
                context = this,
                title = getString(R.string.input_error_title),
                message = getString(R.string.invalid_email_message),
                positiveButtonText = getString(R.string.ok_button),
                negativeButtonText = null,
                positiveAction = null,
                negativeAction = null
            )
        } else if (!isPasswordValid) {
            showUniversalDialog(
                context = this,
                title = getString(R.string.input_error_title),
                message = getString(R.string.invalid_password_message),
                positiveButtonText = getString(R.string.ok_button),
                negativeButtonText = null,
                positiveAction = null,
                negativeAction = null
            )
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
                showUniversalDialog(
                    context = this,
                    title = getString(R.string.google_sign_in_failed_title),
                    message = e.message ?: getString(R.string.google_sign_in_failed_message),
                    positiveButtonText = getString(R.string.ok_button),
                    negativeButtonText = null,
                    positiveAction = null,
                    negativeAction = null
                )
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
                                    showUniversalDialog(
                                        context = this,
                                        title = getString(R.string.database_error_title),
                                        message = dbTask.exception?.message ?: getString(R.string.database_error_message),
                                        positiveButtonText = getString(R.string.ok_button),
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
                        title = getString(R.string.authentication_failed_title),
                        message = task.exception?.message ?: getString(R.string.authentication_failed_message),
                        positiveButtonText = getString(R.string.ok_button),
                        negativeButtonText = null,
                        positiveAction = null,
                        negativeAction = null
                    )
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
                        showUniversalDialog(
                            context = this,
                            title = getString(R.string.email_not_verified_title),
                            message = getString(R.string.email_not_verified_message),
                            positiveButtonText = getString(R.string.ok_button),
                            negativeButtonText = null,
                            positiveAction = null,
                            negativeAction = null
                        )
                        auth.signOut()
                    }
                } else {
                    val message = when (task.exception) {
                        is FirebaseAuthInvalidUserException, is FirebaseAuthInvalidCredentialsException -> getString(R.string.invalid_email_message)
                        else -> task.exception?.message ?: getString(R.string.login_failed_message)
                    }
                    showUniversalDialog(
                        context = this,
                        title = getString(R.string.login_failed_title),
                        message = message,
                        positiveButtonText = getString(R.string.ok_button),
                        negativeButtonText = null,
                        positiveAction = null,
                        negativeAction = null
                    )
                }
            }
    }

    private fun navigateToMain() {
        Toast.makeText(this, getString(R.string.login_success_message), Toast.LENGTH_SHORT).show()
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }

    override fun onBackPressed() {
        if (isTaskRoot) {
            super.onBackPressed()
            finishAffinity()
        } else {
            super.onBackPressed()
            finishAffinity()
        }
    }
}


