package com.example.smartfit.view.welcome

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.EdgeEffect
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.RecyclerView
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
        val tvSkip = findViewById<TextView>(R.id.tvSkip) // Tambahkan ID TextView

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
                navigateToLogin()
            }
        }

        // Teks "Skip" untuk langsung ke LoginActivity
        tvSkip.setOnClickListener {
            navigateToLogin()
        }

        // Ganti teks tombol saat di halaman terakhir
        viewPager.registerOnPageChangeCallback(object : ViewPager2.OnPageChangeCallback() {
            override fun onPageSelected(position: Int) {
                super.onPageSelected(position)
                if (position == slides.size - 1) {
                    btnNext.text = "Get Started"
                    tvSkip.visibility = View.GONE // Sembunyikan Skip di slide terakhir
                } else {
                    btnNext.text = "Next"
                    tvSkip.visibility = View.VISIBLE // Tampilkan Skip
                }
            }
        })

        // Modifikasi warna efek overscroll
        val recyclerView = viewPager.getChildAt(0) as RecyclerView
        recyclerView.edgeEffectFactory = object : RecyclerView.EdgeEffectFactory() {
            override fun createEdgeEffect(view: RecyclerView, direction: Int): EdgeEffect {
                return EdgeEffect(view.context).apply {
                    color = ContextCompat.getColor(view.context, R.color.salmonpink)
                }
            }
        }
    }

    private fun navigateToLogin() {
        val intent = Intent(this, LoginActivity::class.java)
        startActivity(intent)
        finish()
    }
}
