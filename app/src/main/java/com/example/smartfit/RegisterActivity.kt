package com.example.smartfit

import android.content.Intent
import android.os.Bundle
import android.text.InputType
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.example.smartfit.databinding.ActivityRegisterBinding
import com.google.firebase.FirebaseException
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseAuthInvalidCredentialsException
import com.google.firebase.auth.PhoneAuthCredential
import com.google.firebase.auth.PhoneAuthOptions
import com.google.firebase.auth.PhoneAuthProvider
import com.google.firebase.database.FirebaseDatabase
import java.util.concurrent.TimeUnit

class RegisterActivity : AppCompatActivity() {

    private lateinit var binding: ActivityRegisterBinding
    private lateinit var auth: FirebaseAuth
    private lateinit var database: FirebaseDatabase
    private lateinit var verificationId: String

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityRegisterBinding.inflate(layoutInflater)
        setContentView(binding.root)

        auth = FirebaseAuth.getInstance()
        database = FirebaseDatabase.getInstance()

        binding.registerButton.setOnClickListener {
            val email = binding.emailEditText.text.toString().trim()
            val password = binding.passwordEditText.text.toString().trim()
            val phoneNumber = binding.phoneEditText.text.toString().trim()

            if (email.isNotEmpty() && password.isNotEmpty() && phoneNumber.isNotEmpty()) {
                sendVerificationCode(phoneNumber)
            } else {
                showAlertDialog("Input Error", "All fields are required.")
            }
        }
    }

    private fun sendVerificationCode(phoneNumber: String) {
        // Konversi nomor lokal ke format internasional jika perlu
        val formattedPhoneNumber = if (phoneNumber.startsWith("0")) {
            "+62" + phoneNumber.substring(1)
        } else {
            phoneNumber
        }

        val options = PhoneAuthOptions.newBuilder(auth)
            .setPhoneNumber(formattedPhoneNumber) // Nomor telepon pengguna dalam format internasional
            .setTimeout(60L, TimeUnit.SECONDS)    // Timeout OTP
            .setActivity(this)                    // Activity untuk callback
            .setCallbacks(object : PhoneAuthProvider.OnVerificationStateChangedCallbacks() {
                override fun onVerificationCompleted(phoneAuthCredential: PhoneAuthCredential) {
                    // Jika verifikasi otomatis berhasil
                }

                override fun onVerificationFailed(e: FirebaseException) {
                    // Jika verifikasi gagal
                    showAlertDialog("Verification Failed", e.message ?: "Unknown error occurred.")
                }

                override fun onCodeSent(verificationId: String, token: PhoneAuthProvider.ForceResendingToken) {
                    // Jika OTP dikirim, simpan verificationId untuk verifikasi
                    this@RegisterActivity.verificationId = verificationId
                    // Tampilkan dialog untuk memasukkan OTP
                    showOTPDialog()
                }
            })
            .build()
        PhoneAuthProvider.verifyPhoneNumber(options)
    }

    private fun showOTPDialog() {
        val builder = AlertDialog.Builder(this)
        builder.setTitle("Enter OTP")
        val input = EditText(this)
        input.inputType = InputType.TYPE_CLASS_NUMBER
        builder.setView(input)

        builder.setPositiveButton("Verify") { dialog, _ ->
            val otp = input.text.toString()
            if (otp.isNotEmpty()) {
                verifyOTP(otp)
            } else {
                Toast.makeText(this, "OTP is required", Toast.LENGTH_SHORT).show()
            }
        }
        builder.setNegativeButton("Cancel") { dialog, _ ->
            dialog.dismiss()
        }
        builder.show()
    }

    private fun verifyOTP(otp: String) {
        val credential = PhoneAuthProvider.getCredential(verificationId, otp)
        signInWithPhoneAuthCredential(credential)
    }

    private fun signInWithPhoneAuthCredential(credential: PhoneAuthCredential) {
        auth.signInWithCredential(credential)
            .addOnCompleteListener(this) { task ->
                if (task.isSuccessful) {
                    val user = auth.currentUser
                    user?.let {
                        val uid = it.uid
                        val email = binding.emailEditText.text.toString().trim()
                        val currentTime = System.currentTimeMillis()
                        val userRef = database.reference.child("users").child(uid)

                        val userData = mapOf(
                            "email" to email,
                            "phoneNumber" to it.phoneNumber,
                            "createdAt" to currentTime,
                            "displayName" to "",
                            "isNewUser" to true,
                            "lastLogin" to currentTime,
                            "photoURL" to "",
                            "provider" to "phone",
                            "updatedAt" to currentTime
                        )

                        userRef.setValue(userData).addOnCompleteListener { dbTask ->
                            if (dbTask.isSuccessful) {
                                showAlertDialog("Registration Successful", "Your account has been created successfully.", true)
                            } else {
                                showAlertDialog("Database Error", dbTask.exception?.message ?: "Unknown error occurred.", false)
                            }
                        }
                    }
                } else {
                    if (task.exception is FirebaseAuthInvalidCredentialsException) {
                        showAlertDialog("Invalid OTP", "The OTP entered is incorrect.")
                    } else {
                        showAlertDialog("Verification Failed", task.exception?.message ?: "Unknown error occurred.")
                    }
                }
            }
    }

    private fun showAlertDialog(title: String, message: String, isSuccess: Boolean = false) {
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
