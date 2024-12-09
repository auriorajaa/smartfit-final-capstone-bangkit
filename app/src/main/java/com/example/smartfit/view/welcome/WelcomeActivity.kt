package com.example.smartfit.view.welcome

import android.content.Intent
import android.content.SharedPreferences
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
import com.example.smartfit.view.MainActivity
import com.example.smartfit.view.credentials.login.LoginActivity
import com.google.android.material.tabs.TabLayout
import com.google.android.material.tabs.TabLayoutMediator
import com.google.firebase.auth.FirebaseAuth

class WelcomeActivity : AppCompatActivity() {

    private lateinit var sharedPreferences: SharedPreferences
    private lateinit var auth: FirebaseAuth

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_welcome)

        sharedPreferences = getSharedPreferences("AppPrefs", MODE_PRIVATE)
        auth = FirebaseAuth.getInstance()

        // Check if the user is already logged in
        val currentUser = auth.currentUser
        if (currentUser != null) {
            navigateToMain()
            return
        }

        // Check if the welcome activity has been shown before
        if (sharedPreferences.getBoolean("isFirstLaunch", true)) {
            showWelcomeSlides()
        } else {
            navigateToLogin()
        }
    }

    private fun showWelcomeSlides() {
        val viewPager = findViewById<ViewPager2>(R.id.viewPager)
        val tabLayout = findViewById<TabLayout>(R.id.tabLayout)
        val btnNext = findViewById<Button>(R.id.btnNext)
        val tvSkip = findViewById<TextView>(R.id.tvSkip)

        val slides = listOf(
            WelcomeSlide(
                R.drawable.image_welcome1,
                "Welcome to SmartFit!",
                "Discover the perfect outfit recommendations tailored to your unique skin tone."
            ),
            WelcomeSlide( R.drawable.image_welcome2,
                "Explore Your Unique Style",
                "Browse and find the best outfits effortlessly, curated to match your preferences."
            ),
            WelcomeSlide( R.drawable.image_welcome3,
                "Personalized for You",
                "SmartFit adapts to your style, offering outfits that complement your skin tone beautifully."
            )
        )
        viewPager.adapter = WelcomeAdapter(slides, viewPager)
        TabLayoutMediator(tabLayout, viewPager) { _, _ -> }.attach()

        btnNext.setOnClickListener {
            if (viewPager.currentItem < slides.size - 1) {
                viewPager.currentItem += 1
            } else {
                markWelcomeShown()
                navigateToLogin()
            }
        }

        tvSkip.setOnClickListener {
            markWelcomeShown()
            navigateToLogin()
        }

        viewPager.registerOnPageChangeCallback(object : ViewPager2.OnPageChangeCallback() {
            override fun onPageSelected(position: Int) {
                super.onPageSelected(position)
                if (position == slides.size - 1) {
                    btnNext.text = "Get Started"
                    tvSkip.visibility = View.GONE
                } else {
                    btnNext.text = "Next"
                    tvSkip.visibility = View.VISIBLE
                }
            }
        })

        val recyclerView = viewPager.getChildAt(0) as RecyclerView
        recyclerView.edgeEffectFactory = object : RecyclerView.EdgeEffectFactory() {
            override fun createEdgeEffect(view: RecyclerView, direction: Int): EdgeEffect {
                return EdgeEffect(view.context).apply {
                    color = ContextCompat.getColor(view.context, R.color.salmonpink)
                }
            }
        }
    }

    private fun markWelcomeShown() {
        sharedPreferences.edit().putBoolean("isFirstLaunch", false).apply() }

    private fun navigateToLogin() {
        val intent = Intent(this, LoginActivity::class.java)
        startActivity(intent)
        finish()
    }

    private fun navigateToMain() {
        val intent = Intent(this, MainActivity::class.java)
        startActivity(intent)
        finish()
    }
}
