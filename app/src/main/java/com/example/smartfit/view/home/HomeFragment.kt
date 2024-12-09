package com.example.smartfit.view.home

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import androidx.fragment.app.Fragment
import com.example.smartfit.R
import com.example.smartfit.view.detection.camera.CameraActivity
import com.example.smartfit.view.setting.SettingActivity
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.database.*

class HomeFragment : Fragment() {

    private lateinit var auth: FirebaseAuth
    private lateinit var database: FirebaseDatabase
    private lateinit var userRef: DatabaseReference

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        // Inflate the layout
        val view = inflater.inflate(R.layout.fragment_home, container, false)

        // Initialize Firebase Auth and Database
        auth = FirebaseAuth.getInstance()
        database = FirebaseDatabase.getInstance()
        val currentUser = auth.currentUser

        // Initialize TextViews
        val tvUsername = view.findViewById<TextView>(R.id.tv_username)

        if (currentUser != null) {
            userRef = database.reference.child("users").child(currentUser.uid)
            userRef.addValueEventListener(object : ValueEventListener {
                override fun onDataChange(snapshot: DataSnapshot) {
                    val displayName = snapshot.child("displayName").getValue(String::class.java)
                    if (!displayName.isNullOrEmpty()) {
                        tvUsername.text = displayName
                    }
                }

                override fun onCancelled(error: DatabaseError) {
                    // Handle database error
                }
            })
        }

        // Set click listener for cv_setting
        val cvSetting = view.findViewById<View>(R.id.cv_setting)
        cvSetting.setOnClickListener {
            // Navigate to SettingActivity
            val intent = Intent(requireContext(), SettingActivity::class.java)
            startActivity(intent)
        }

        val btnLetsStart = view.findViewById<Button>(R.id.btn_lets_start)
        btnLetsStart.setOnClickListener {
            val intent = Intent(requireContext(), CameraActivity::class.java)
            startActivity(intent)
        }

        return view
    }
}
