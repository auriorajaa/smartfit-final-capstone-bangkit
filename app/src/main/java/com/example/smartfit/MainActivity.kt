package com.example.smartfit

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.example.smartfit.databinding.ActivityMainBinding
import com.example.smartfit.databinding.DialogReauthenticateBinding
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInClient
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.firebase.auth.EmailAuthProvider
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseAuthRecentLoginRequiredException
import com.google.firebase.auth.GoogleAuthProvider
import com.google.firebase.database.FirebaseDatabase

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var auth: FirebaseAuth
    private lateinit var database: FirebaseDatabase
    private lateinit var googleSignInClient: GoogleSignInClient

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        auth = FirebaseAuth.getInstance()
        database = FirebaseDatabase.getInstance()

        // Konfigurasi GoogleSignInClient
        val gso = GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
            .requestIdToken(getString(R.string.default_web_client_id))
            .requestEmail()
            .build()

        googleSignInClient = GoogleSignIn.getClient(this, gso)

        binding.logoutButton.setOnClickListener {
            auth.signOut()
            val intent = Intent(this, WelcomeActivity::class.java)
            startActivity(intent)
            finish()
        }

        binding.deleteAccountButton.setOnClickListener {
            showDeleteAccountDialog()
        }

        checkUserSession()
    }

    private fun checkUserSession() {
        val currentUser = auth.currentUser
        if (currentUser == null) {
            val intent = Intent(this, WelcomeActivity::class.java)
            startActivity(intent)
            finish()
        }
    }

    private fun showDeleteAccountDialog() {
        val builder = AlertDialog.Builder(this)
        builder.setTitle("Delete Account")
        builder.setMessage("Are you sure you want to delete your account? This action cannot be undone.")
        builder.setPositiveButton("Yes") { dialog, _ ->
            dialog.dismiss()
            reauthenticateAndDeleteAccount()
        }
        builder.setNegativeButton("No") { dialog, _ ->
            dialog.dismiss()
        }
        val dialog = builder.create()
        dialog.show()
    }

    private fun reauthenticateAndDeleteAccount() {
        val currentUser = auth.currentUser
        currentUser?.let {
            val providers = it.providerData.map { provider -> provider.providerId }
            if (providers.contains(GoogleAuthProvider.PROVIDER_ID)) {
                // Mendapatkan ID token dari Google SignIn Client
                val signInAccount = GoogleSignIn.getLastSignedInAccount(this)
                if (signInAccount != null) {
                    val idToken = signInAccount.idToken
                    if (idToken != null) {
                        // Re-autentikasi menggunakan Google provider
                        val credential = GoogleAuthProvider.getCredential(idToken, null)
                        it.reauthenticate(credential).addOnCompleteListener { reauthTask ->
                            if (reauthTask.isSuccessful) {
                                // Lanjutkan dengan penghapusan akun
                                deleteUserAccount()
                            } else {
                                showAlertDialog("Re-authentication Failed", "Please sign in again and try deleting your account.", false)
                            }
                        }
                    } else {
                        showAlertDialog("Failed to get ID token", "ID token is null.", false)
                    }
                } else {
                    showAlertDialog("No Google Sign-In Account Found", "Please sign in with Google again.", false)
                }
            } else if (providers.contains(EmailAuthProvider.PROVIDER_ID)) {
                // Re-autentikasi menggunakan email provider
                val email = it.email
                if (email != null) {
                    showEmailPasswordReauthDialog(email)
                } else {
                    showAlertDialog("Re-authentication Failed", "Email not found for re-authentication.", false)
                }
            } else {
                // Unsupported provider, show error
                showAlertDialog("Re-authentication Failed", "Unsupported authentication provider.", false)
            }
        }
    }

    private fun showEmailPasswordReauthDialog(email: String) {
        val builder = AlertDialog.Builder(this)
        val bindingDialog = DialogReauthenticateBinding.inflate(layoutInflater)
        builder.setView(bindingDialog.root)

        bindingDialog.emailEditText.setText(email) // Prasetel email pengguna

        builder.setPositiveButton("Authenticate") { dialog, _ ->
            val password = bindingDialog.passwordEditText.text.toString()
            val credential = EmailAuthProvider.getCredential(email, password)

            auth.currentUser?.reauthenticate(credential)?.addOnCompleteListener { task ->
                if (task.isSuccessful) {
                    // Lanjutkan dengan penghapusan akun setelah autentikasi ulang berhasil
                    deleteUserAccount()
                } else {
                    showAlertDialog("Authentication Failed", "Re-authentication failed. Please try again.", false)
                }
            }
        }
        builder.setNegativeButton("Cancel") { dialog, _ ->
            dialog.dismiss()
        }
        builder.create().show()
    }

    private fun deleteUserAccount() {
        val currentUser = auth.currentUser
        currentUser?.let {
            val uid = it.uid
            val userRef = database.reference.child("users").child(uid)

            // Delete user data from Realtime Database
            userRef.removeValue().addOnCompleteListener { dbTask ->
                if (dbTask.isSuccessful) {
                    // Delete user from Firebase Authentication
                    currentUser.delete().addOnCompleteListener { authTask ->
                        if (authTask.isSuccessful) {
                            showAlertDialog("Account Deleted", "Your account has been successfully deleted.", true)
                        } else {
                            showAlertDialog("Deletion Failed", authTask.exception?.message ?: "Unknown error occurred.", false)
                        }
                    }
                } else {
                    showAlertDialog("Deletion Failed", dbTask.exception?.message ?: "Unknown error occurred.", false)
                }
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
                auth.signOut()
                val intent = Intent(this, WelcomeActivity::class.java)
                startActivity(intent)
                finish()
            }
        }
        val dialog = builder.create()
        dialog.show()
    }
}
