package com.example.smartfit.view.setting.account

import android.content.Intent
import android.graphics.drawable.AnimationDrawable
import android.os.Bundle
import android.widget.TextView
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import com.example.smartfit.R
import com.example.smartfit.databinding.DialogReauthenticateBinding
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
        val builder = MaterialAlertDialogBuilder(this)
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
                val signInAccount = GoogleSignIn.getLastSignedInAccount(this)
                if (signInAccount != null) {
                    val idToken = signInAccount.idToken
                    if (idToken != null) {
                        val credential = GoogleAuthProvider.getCredential(idToken, null)
                        it.reauthenticate(credential).addOnCompleteListener { reauthTask ->
                            if (reauthTask.isSuccessful) {
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
                val email = it.email
                if (email != null) {
                    showEmailPasswordReauthDialog(email)
                } else {
                    showAlertDialog("Re-authentication Failed", "Email not found for re-authentication.", false)
                }
            } else {
                showAlertDialog("Re-authentication Failed", "Unsupported authentication provider.", false)
            }
        }
    }

    private fun showEmailPasswordReauthDialog(email: String) {
        val builder = MaterialAlertDialogBuilder(this)
        val bindingDialog = DialogReauthenticateBinding.inflate(layoutInflater)
        builder.setView(bindingDialog.root)

        bindingDialog.emailEditText.setText(email)

        builder.setPositiveButton("Authenticate") { dialog, _ ->
            val password = bindingDialog.passwordEditText.text.toString()
            val credential = EmailAuthProvider.getCredential(email, password)

            auth.currentUser?.reauthenticate(credential)?.addOnCompleteListener { task ->
                if (task.isSuccessful) {
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
            val historyRef = database.reference.child("prediction_history").child(uid)

            userRef.removeValue().continueWithTask { userTask ->
                if (userTask.isSuccessful) {
                    historyRef.removeValue()
                } else {
                    throw userTask.exception ?: Exception("Failed to delete user data")
                }
            }.addOnCompleteListener { task ->
                if (task.isSuccessful) {
                    currentUser.delete().addOnCompleteListener { authTask ->
                        if (authTask.isSuccessful) {
                            showAlertDialog("Account Deleted", "Your account and history have been successfully deleted.", true) {
                                val intent = Intent(this, LoginActivity::class.java)
                                startActivity(intent)
                                finish()
                            }
                        } else {
                            showAlertDialog("Deletion Failed", authTask.exception?.message ?: "Unknown error occurred.", false)
                        }
                    }
                } else {
                    showAlertDialog("Deletion Failed", task.exception?.message ?: "Unknown error occurred.", false)
                }
            }
        }
    }

    private fun showAlertDialog(title: String, message: String, isSuccess: Boolean, onDismissAction: (() -> Unit)? = null) {
        val builder = MaterialAlertDialogBuilder(this)
        builder.setTitle(title)
        builder.setMessage(message)
        builder.setPositiveButton("OK") { dialog, _ ->
            dialog.dismiss()
            onDismissAction?.invoke()
        }
        val dialog = builder.create()
        dialog.show()
    }
}
