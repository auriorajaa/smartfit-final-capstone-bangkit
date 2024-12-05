package com.example.smartfit.view.welcome

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import androidx.viewpager2.widget.ViewPager2
import com.example.smartfit.R
import com.example.smartfit.view.credentials.login.LoginActivity

class WelcomeAdapter(
    private val slides: List<WelcomeSlide>,
    private val viewPager: ViewPager2 // Tambahkan ViewPager2 untuk navigasi antar slide
) : RecyclerView.Adapter<WelcomeAdapter.OnboardingViewHolder>() {

    inner class OnboardingViewHolder(private val view: View) : RecyclerView.ViewHolder(view) {
        fun bind(slide: WelcomeSlide, position: Int, isLast: Boolean) {
            val imageView = view.findViewById<ImageView>(R.id.imageView)
            val titleText = view.findViewById<TextView>(R.id.titleText)
            val descriptionText = view.findViewById<TextView>(R.id.descriptionText)
            val button = view.findViewById<Button>(R.id.button)

            // Atur data ke komponen UI
            imageView.setImageResource(slide.imageRes)
            titleText.text = slide.title
            descriptionText.text = slide.description

            // Atur teks tombol dan aksi sesuai posisi slide
            if (isLast) {
                button.text = "Get Started"
                button.setOnClickListener {
                    val context = view.context
                    context.startActivity(Intent(context, LoginActivity::class.java))
                    (context as? Activity)?.finish() // Tutup OnboardingActivity
                }
            } else {
                button.text = "Next"
                button.setOnClickListener {
                    viewPager.currentItem = position + 1 // Pindah ke slide berikutnya
                }
            }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): OnboardingViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_slide, parent, false)
        return OnboardingViewHolder(view)
    }

    override fun onBindViewHolder(holder: OnboardingViewHolder, position: Int) {
        holder.bind(slides[position], position, position == slides.size - 1) // Tandai slide terakhir
    }

    override fun getItemCount(): Int = slides.size
}
