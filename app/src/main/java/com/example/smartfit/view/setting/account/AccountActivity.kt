package com.example.smartfit.view.setting.account

import android.content.Intent
import android.graphics.drawable.AnimationDrawable
import android.os.Bundle
import android.widget.TextView
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import com.example.smartfit.R
import com.example.smartfit.databinding.DialogReauthenticateBinding
import com.example.smartfit.utils.showUniversalDialog
import com.example.smartfit.view.credentials.login.LoginActivity
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.firebase.auth.*
import com.google.firebase.database.*
import com.google.android.material.card.MaterialCardView
import com.google.android.material.dialog.MaterialAlertDialogBuilder

class AccountActivity : AppCompatActivity() {

    private lateinit var auth: FirebaseAuth
    private lateinit var database: FirebaseDatabase
    private lateinit var userRef: DatabaseReference

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_account)

        // Initialize Firebase Auth and Database
        auth = FirebaseAuth.getInstance()
        database = FirebaseDatabase.getInstance()
        val currentUser = auth.currentUser

        // Initialize TextViews
        val tvUsername = findViewById<TextView>(R.id.tv_name_account)
        val tvEmail = findViewById<TextView>(R.id.tv_email_format)

        if (currentUser != null) {
            userRef = database.reference.child("users").child(currentUser.uid)
            userRef.addValueEventListener(object : ValueEventListener {
                override fun onDataChange(snapshot: DataSnapshot) {
                    val displayName = snapshot.child("displayName").getValue(String::class.java)
                    val email = currentUser.email

                    if (!displayName.isNullOrEmpty()) {
                        tvUsername.text = displayName
                    }
                    if (!email.isNullOrEmpty()) {
                        tvEmail.text = email
                    }
                }

                override fun onCancelled(error: DatabaseError) {
                    // Handle database error
                }
            })
        }

        // Mengatur background bergerak
        val constraintLayout: ConstraintLayout = findViewById(R.id.main)
        val animationDrawable = constraintLayout.background as AnimationDrawable
        animationDrawable.setEnterFadeDuration(1500)
        animationDrawable.setExitFadeDuration(3000)
        animationDrawable.start()

        // Set click listener for back button
        val backButton = findViewById<MaterialCardView>(R.id.btn_back_account)
        backButton.setOnClickListener {
            finish()
        }

        // Set click listener for delete account button
        val deleteButton = findViewById<MaterialCardView>(R.id.cv_delete_account)
        deleteButton.setOnClickListener {
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
                        }
                    } else {
                        showUniversalDialog(
                            context = this,
                            title = getString(R.string.reauth_id_token_failed_title),
                            message = getString(R.string.reauth_id_token_failed_message),
                            positiveButtonText = getString(R.string.ok),
                            negativeButtonText = null,
                            positiveAction = null,
                            negativeAction = null
                        )
                    }
                } else {
                    showUniversalDialog(
                        context = this,
                        title = getString(R.string.reauth_google_account_failed_title),
                        message = getString(R.string.reauth_google_account_failed_message),
                        positiveButtonText = getString(R.string.ok),
                        negativeButtonText = null,
                        positiveAction = null,
                        negativeAction = null
                    )
                }
            } else if (providers.contains(EmailAuthProvider.PROVIDER_ID)) {
                val email = it.email
                if (email != null) {
                    showEmailPasswordReauthDialog(email)
                } else {
                    showUniversalDialog(
                        context = this,
                        title = getString(R.string.reauth_failed_title),
                        message = getString(R.string.reauth_email_not_found_message),
                        positiveButtonText = getString(R.string.ok),
                        negativeButtonText = null,
                        positiveAction = null,
                        negativeAction = null
                    )
                }
            } else {
                showUniversalDialog(
                    context = this,
                    title = getString(R.string.reauth_failed_title),
                    message = getString(R.string.reauth_unsupported_provider_message),
                    positiveButtonText = getString(R.string.ok),
                    negativeButtonText = null,
                    positiveAction = null,
                    negativeAction = null
                )
            }
        }
    }

    private fun showEmailPasswordReauthDialog(email: String) {
        val builder = MaterialAlertDialogBuilder(this)
        val bindingDialog = DialogReauthenticateBinding.inflate(layoutInflater)
        builder.setView(bindingDialog.root)

        bindingDialog.emailEditText.setText(email)

        builder.setPositiveButton(getString(R.string.reauth_positive)) { dialog, _ ->
            val password = bindingDialog.passwordEditText.text.toString()
            val credential = EmailAuthProvider.getCredential(email, password)

            auth.currentUser?.reauthenticate(credential)?.addOnCompleteListener { task ->
                if (task.isSuccessful) {
                    deleteUserAccount()
                } else {
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
                        } else {
                            showUniversalDialog(
                                context = this,
                                title = getString(R.string.delete_failed_title),
                                message = authTask.exception?.message ?: getString(R.string.unknown_error_message),
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
                        title = getString(R.string.delete_failed_title),
                        message = task.exception?.message ?: getString(R.string.unknown_error_message),
                        positiveButtonText = getString(R.string.ok),
                        negativeButtonText = null,
                        positiveAction = null,
                        negativeAction = null
                    )
                }
            }
        }
    }

    private fun showAlertDialog(title: String, message: String, isSuccess: Boolean, onDismissAction: (() -> Unit)? = null) {
        showUniversalDialog(
            context = this,
            title = title,
            message = message,
            positiveButtonText = getString(R.string.ok),
            negativeButtonText = null,
            positiveAction = { onDismissAction?.invoke() },
            negativeAction = null
        )
    }
}
