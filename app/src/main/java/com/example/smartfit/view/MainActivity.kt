package com.example.smartfit.view

import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.drawable.AnimationDrawable
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.view.WindowInsetsController
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.fragment.app.Fragment
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkRequest
import com.example.smartfit.R
import com.example.smartfit.utils.NotificationHelper
import com.example.smartfit.utils.NotificationWorker
import com.example.smartfit.view.history.HistoryFragment
import com.example.smartfit.view.credentials.login.LoginActivity
import com.example.smartfit.view.home.HomeFragment
import com.example.smartfit.view.news.NewsFragment
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.firebase.auth.FirebaseAuth
import java.util.concurrent.TimeUnit

class MainActivity : AppCompatActivity() {

    private lateinit var bottomNavigationView: BottomNavigationView
    private lateinit var auth: FirebaseAuth
    private val hideHandler = Handler(Looper.getMainLooper())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        auth = FirebaseAuth.getInstance()

        // Menyembunyikan tombol navigasi saja
        val controller = ViewCompat.getWindowInsetsController(window.decorView)
        controller?.hide(WindowInsetsCompat.Type.navigationBars())
        controller?.systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_DEFAULT

        window.decorView.setOnSystemUiVisibilityChangeListener {
            hideHandler.postDelayed({
                controller?.hide(WindowInsetsCompat.Type.navigationBars())
            }, 5000)
        }

        window.apply {
            decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN or
                    View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION or
                    View.SYSTEM_UI_FLAG_LAYOUT_STABLE

            statusBarColor = Color.TRANSPARENT

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                insetsController?.setSystemBarsAppearance(
                    WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS or
                            WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS,
                    WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS or
                            WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS
                )
            }
        }

        // Mengatur BottomNavigationView
        bottomNavigationView = findViewById(R.id.bottom_nav)

        // Membuka fragment awal (HomeFragment)
        if (savedInstanceState == null) {
            openFragment(HomeFragment())
        }

        // Menangani event klik item pada BottomNavigationView
        bottomNavigationView.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_home -> {
                    openFragment(HomeFragment())
                    true
                }

                R.id.nav_news -> {
                    openFragment(NewsFragment())
                    true
                }

                R.id.nav_bookmark -> {
                    openFragment(HistoryFragment())
                    true
                }

                else -> false
            }
        }

        // Mengatur background bergerak
        val constraintLayout: ConstraintLayout = findViewById(R.id.main)
        val animationDrawable = constraintLayout.background as AnimationDrawable
        animationDrawable.setEnterFadeDuration(1500)
        animationDrawable.setExitFadeDuration(3000)
        animationDrawable.start()

        // Panggil createNotificationChannel
        NotificationHelper.createNotificationChannel(this)

        // Cek waktu notifikasi terakhir
        val sharedPreferences = getSharedPreferences("NotificationPrefs", Context.MODE_PRIVATE)
        val lastNotificationTime = sharedPreferences.getLong("lastNotificationTime", 0L)
        val currentTime = System.currentTimeMillis()
        val timeDiff = currentTime - lastNotificationTime

        // Jika lebih dari 12 jam sejak notifikasi terakhir, jadwalkan ulang
        if (timeDiff >= TimeUnit.HOURS.toMillis(12)) {
            val workRequest: WorkRequest =
                PeriodicWorkRequestBuilder<NotificationWorker>(12, TimeUnit.HOURS)
                    .build()
            WorkManager.getInstance(this).enqueue(workRequest)
        }
    }

    override fun onStart() {
        super.onStart()

        val currentUser = auth.currentUser
        if (currentUser == null) {
            val intent = Intent(this, LoginActivity::class.java)
            startActivity(intent)
            finish()
        }
    }

    // Fungsi untuk mengganti fragment
    private fun openFragment(fragment: Fragment) {
        supportFragmentManager.beginTransaction()
            .replace(R.id.fragment_container, fragment)
            .commit()
    }
}
