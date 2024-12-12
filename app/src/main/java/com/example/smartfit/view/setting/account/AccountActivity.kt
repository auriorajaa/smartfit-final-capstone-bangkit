package com.example.smartfit.view.setting.account

import android.content.Intent
import android.graphics.drawable.AnimationDrawable
import android.os.Bundle
import android.widget.TextView
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.bumptech.glide.Glide
import com.example.smartfit.R
import com.example.smartfit.databinding.ActivityAccountBinding
import com.example.smartfit.databinding.DialogReauthenticateBinding
import com.example.smartfit.utils.showUniversalDialog
import com.example.smartfit.view.credentials.login.LoginActivity
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.firebase.auth.*
import com.google.firebase.database.*
import com.google.android.material.card.MaterialCardView
import com.google.android.material.dialog.MaterialAlertDialogBuilder

class AccountActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAccountBinding
    private lateinit var auth: FirebaseAuth
    private lateinit var database: FirebaseDatabase
    private lateinit var userRef: DatabaseReference

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // Inisialisasi View Binding
        binding = ActivityAccountBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val controller = ViewCompat.getWindowInsetsController(window.decorView)
        controller?.hide(WindowInsetsCompat.Type.navigationBars())
        controller?.systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_DEFAULT

        window.decorView.setOnSystemUiVisibilityChangeListener {
            controller?.hide(WindowInsetsCompat.Type.navigationBars())
        }

        // Initialize Firebase Auth and Database
        auth = FirebaseAuth.getInstance()
        database = FirebaseDatabase.getInstance()
        val currentUser = auth.currentUser

        if (currentUser != null) {
            userRef = database.reference.child("users").child(currentUser.uid)
            userRef.addValueEventListener(object : ValueEventListener {
                override fun onDataChange(snapshot: DataSnapshot) {
                    val displayName = snapshot.child("displayName").getValue(String::class.java)
                    val email = currentUser.email
                    val photoURL = snapshot.child("photoURL").getValue(String::class.java)

                    if (!displayName.isNullOrEmpty()) {
                        binding.tvNameAccount.text = displayName
                    }
                    if (!email.isNullOrEmpty()) {
                        binding.tvEmailFormat.text = email
                    }
                    if (!photoURL.isNullOrEmpty()) {
                        Glide.with(this@AccountActivity)
                            .load(photoURL)
                            .into(binding.imageView4)
                    }
                }

                override fun onCancelled(error: DatabaseError) {
                    // Handle database error
                }
            })
        }

        // Mengatur background bergerak
        val animationDrawable = binding.main.background as AnimationDrawable
        animationDrawable.setEnterFadeDuration(1500)
        animationDrawable.setExitFadeDuration(3000)
        animationDrawable.start()

        // Set click listener for back button
        binding.btnBackAccount.setOnClickListener {
            finish()
        }

        // Set click listener for delete account button
        binding.cvDeleteAccount.setOnClickListener {
            showDeleteAccountDialog()
        }
    }

    private fun showDeleteAccountDialog() {
        showUniversalDialog(
            context = this,
            title = getString(R.string.delete_account_title),
            message = getString(R.string.delete_account_message),
            positiveButtonText = getString(R.string.delete_account_positive),
            negativeButtonText = getString(R.string.delete_account_negative),
            positiveAction = { reauthenticateAndDeleteAccount() },
            negativeAction = { /* Do nothing */ }
        )
    }

    private fun reauthenticateAndDeleteAccount() {
        val currentUser = auth.currentUser
        currentUser?.let {
            val providers = it.providerData.map { provider -> provider.providerId }
            if (providers.contains(GoogleAuthProvider.PROVIDER_ID)) {
                val signInAccount = GoogleSignIn.getLastSignedInAccount(this)
                if (signInAccount != null) {
                    val idToken = signInAccount.idToken
                    if (idToken != null) {
                        val credential = GoogleAuthProvider.getCredential(idToken, null)
                        it.reauthenticate(credential).addOnCompleteListener { reauthTask ->
                            if (reauthTask.isSuccessful) {
                                deleteUserAccount()
                            } else {
                                showReauthFailedDialog()
                            }
                        }
                    } else {
                        showReauthFailedDialog()
                    }
                } else {
                    showReauthFailedDialog()
                }
            } else if (providers.contains(EmailAuthProvider.PROVIDER_ID)) {
                val email = it.email
                if (email != null) {
                    showEmailPasswordReauthDialog(email)
                } else {
                    showReauthFailedDialog()
                }
            } else {
                showReauthFailedDialog()
            }
        }
    }

    private fun showEmailPasswordReauthDialog(email: String) {
        val builder = MaterialAlertDialogBuilder(this)
        val dialogBinding = DialogReauthenticateBinding.inflate(layoutInflater)
        builder.setView(dialogBinding.root)

        dialogBinding.emailEditText.setText(email)

        builder.setPositiveButton(getString(R.string.reauth_positive)) { dialog, _ ->
            val password = dialogBinding.passwordEditText.text.toString()
            val credential = EmailAuthProvider.getCredential(email, password)

            auth.currentUser?.reauthenticate(credential)?.addOnCompleteListener { task ->
                if (task.isSuccessful) {
                    deleteUserAccount()
                } else {
                    showReauthFailedDialog()
                }
            }
        }
        builder.setNegativeButton(getString(R.string.reauth_negative)) { dialog, _ ->
            dialog.dismiss()
        }
        builder.create().show()
    }

    private fun deleteUserAccount() {
        val currentUser = auth.currentUser
        currentUser?.let {
            val uid = it.uid
            val userRef = database.reference.child("users").child(uid)
            val historyRef = database.reference.child("prediction_history").child(uid)

            userRef.removeValue().continueWithTask { userTask ->
                if (userTask.isSuccessful) {
                    historyRef.removeValue()
                } else {
                    throw userTask.exception ?: Exception(getString(R.string.delete_data_failed_message))
                }
            }.addOnCompleteListener { task ->
                if (task.isSuccessful) {
                    currentUser.delete().addOnCompleteListener { authTask ->
                        if (authTask.isSuccessful) {
                            showDeleteSuccessDialog()
                        } else {
                            showDeleteFailedDialog(authTask.exception?.message)
                        }
                    }
                } else {
                    showDeleteFailedDialog(task.exception?.message)
                }
            }
        }
    }

    private fun showReauthFailedDialog() {
        showUniversalDialog(
            context = this,
            title = getString(R.string.reauth_failed_title),
            message = getString(R.string.reauth_failed_message),
            positiveButtonText = getString(R.string.ok),
            negativeButtonText = null,
            positiveAction = null,
            negativeAction = null
        )
    }

    private fun showDeleteSuccessDialog() {
        showUniversalDialog(
            context = this,
            title = getString(R.string.delete_success_title),
            message = getString(R.string.delete_success_message),
            positiveButtonText = getString(R.string.ok),
            negativeButtonText = null,
            positiveAction = {
                val intent = Intent(this, LoginActivity::class.java)
                startActivity(intent)
                finish()
            },
            negativeAction = null
        )
    }

    private fun showDeleteFailedDialog(errorMessage: String?) {
        showUniversalDialog(
            context = this,
            title = getString(R.string.delete_failed_title),
            message = errorMessage ?: getString(R.string.unknown_error_message),
            positiveButtonText = getString(R.string.ok),
            negativeButtonText = null,
            positiveAction = null,
            negativeAction = null
        )
    }
}
