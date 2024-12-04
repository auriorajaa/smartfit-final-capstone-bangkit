package com.example.smartfit.view.home

import android.content.Intent
import android.os.Bundle
import androidx.fragment.app.Fragment
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import com.example.smartfit.R
import com.example.smartfit.view.detection.camera.CameraActivity
import com.example.smartfit.view.setting.SettingActivity

class HomeFragment : Fragment() {

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        // Inflate the layout
        val view = inflater.inflate(R.layout.fragment_home, container, false)

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