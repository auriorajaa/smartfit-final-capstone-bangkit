package com.example.smartfit

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.example.smartfit.databinding.ItemOutfitRecommendationBinding
import com.example.smartfit.network.OutfitRecommendation

class OutfitRecommendationAdapter(private val items: List<OutfitRecommendation>) :
    RecyclerView.Adapter<OutfitRecommendationAdapter.ViewHolder>() {

    inner class ViewHolder(private val binding: ItemOutfitRecommendationBinding) :
        RecyclerView.ViewHolder(binding.root) {
        fun bind(item: OutfitRecommendation) {
            binding.itemName.text = item.item
            binding.itemDescription.text = item.description
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemOutfitRecommendationBinding.inflate(
            LayoutInflater.from(parent.context), parent, false)
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(items[position])
    }

    override fun getItemCount(): Int = items.size
}
