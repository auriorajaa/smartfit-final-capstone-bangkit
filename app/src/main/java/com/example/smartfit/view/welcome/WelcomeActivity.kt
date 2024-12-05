package com.example.smartfit.view.welcome

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import androidx.appcompat.app.AppCompatActivity
import androidx.viewpager2.widget.ViewPager2
import com.example.smartfit.R
import com.example.smartfit.view.credentials.login.LoginActivity
import com.google.android.material.tabs.TabLayout
import com.google.android.material.tabs.TabLayoutMediator

class WelcomeActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_welcome)

        val viewPager = findViewById<ViewPager2>(R.id.viewPager)
        val tabLayout = findViewById<TabLayout>(R.id.tabLayout)
        val btnNext = findViewById<Button>(R.id.btnNext)

        // Data slide
        val slides = listOf(
            WelcomeSlide(R.drawable.image_welcome1, "Welcome to SmartFit!", "Discover the perfect outfit recommendations tailored to your unique skin tone."),
            WelcomeSlide(R.drawable.image_welcome2, "Explore Your Unique Style", "Browse and find the best outfits effortlessly, curated to match your preferences."),
            WelcomeSlide(R.drawable.image_welcome3, "Personalized for You", "SmartFit adapts to your style, offering outfits that complement your skin tone beautifully.")
        )

        // Set adapter untuk ViewPager2
        viewPager.adapter = WelcomeAdapter(slides, viewPager)

        // Sinkronisasi TabLayout dan ViewPager2
        TabLayoutMediator(tabLayout, viewPager) { _, _ -> }.attach()

        // Tombol Next/Get Started
        btnNext.setOnClickListener {
            if (viewPager.currentItem < slides.size - 1) {
                // Pindah ke halaman berikutnya
                viewPager.currentItem = viewPager.currentItem + 1
            } else {
                // Halaman terakhir: Pindah ke LoginActivity
                val intent = Intent(this, LoginActivity::class.java)
                startActivity(intent)
                finish()
            }
        }

        // Ganti teks tombol saat di halaman terakhir
        viewPager.registerOnPageChangeCallback(object : ViewPager2.OnPageChangeCallback() {
            override fun onPageSelected(position: Int) {
                super.onPageSelected(position)
                if (position == slides.size - 1) {
                    btnNext.text = "Get Started"
                } else {
                    btnNext.text = "Next"
                }
            }
        })
    }
}


