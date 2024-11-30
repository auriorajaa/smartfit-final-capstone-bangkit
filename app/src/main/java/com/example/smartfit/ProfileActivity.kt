package com.example.smartfit

import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import com.example.smartfit.databinding.ActivityProfileBinding
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.database.*

class ProfileActivity : AppCompatActivity() {

    private lateinit var binding: ActivityProfileBinding
    private lateinit var auth: FirebaseAuth
    private lateinit var database: FirebaseDatabase

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityProfileBinding.inflate(layoutInflater)
        setContentView(binding.root)

        auth = FirebaseAuth.getInstance()
        database = FirebaseDatabase.getInstance()

        loadUserProfile()
    }

    private fun loadUserProfile() {
        binding.loadingProgressBar.visibility = View.VISIBLE
        binding.displayNameTextView.visibility = View.GONE
        binding.emailTextView.visibility = View.GONE

        val currentUser = auth.currentUser
        if (currentUser != null) {
            val userRef = database.reference.child("users").child(currentUser.uid)
            userRef.addValueEventListener(object : ValueEventListener {
                override fun onDataChange(snapshot: DataSnapshot) {
                    val displayName = snapshot.child("displayName").getValue(String::class.java)
                    val email = snapshot.child("email").getValue(String::class.java)

                    binding.displayNameTextView.text = displayName
                    binding.emailTextView.text = email

                    binding.loadingProgressBar.visibility = View.GONE
                    binding.displayNameTextView.visibility = View.VISIBLE
                    binding.emailTextView.visibility = View.VISIBLE
                }

                override fun onCancelled(error: DatabaseError) {
                    // Handle possible errors
                    binding.loadingProgressBar.visibility = View.GONE
                }
            })
        } else {
            binding.loadingProgressBar.visibility = View.GONE
        }
    }
}
