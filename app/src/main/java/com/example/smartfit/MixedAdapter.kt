package com.example.smartfit

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.example.smartfit.databinding.ItemCombinedBinding
import com.example.smartfit.network.AmazonProduct
import com.example.smartfit.network.OutfitRecommendation

class MixedAdapter(
    private val context: Context,
    private val amazonProducts: List<AmazonProduct>,
    private val outfitRecommendations: List<OutfitRecommendation>
) : RecyclerView.Adapter<MixedAdapter.CombinedViewHolder>() {

    inner class CombinedViewHolder(private val binding: ItemCombinedBinding) :
        RecyclerView.ViewHolder(binding.root) {
        init {
            binding.productImage.setOnClickListener {
                val position = adapterPosition
                if (position != RecyclerView.NO_POSITION) {
                    val product = amazonProducts[position]
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(product.detail_url))
                    context.startActivity(intent)
                }
            }
        }

        fun bind(product: AmazonProduct, recommendation: OutfitRecommendation) {
            Glide.with(context).load(product.pic).into(binding.productImage)
            binding.itemName.text = recommendation.item
            binding.itemDescription.text = recommendation.description
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): CombinedViewHolder {
        val binding = ItemCombinedBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return CombinedViewHolder(binding)
    }

    override fun onBindViewHolder(holder: CombinedViewHolder, position: Int) {
        val product = amazonProducts[position]
        val recommendation = outfitRecommendations[position]
        holder.bind(product, recommendation)
    }

    override fun getItemCount(): Int = minOf(amazonProducts.size, outfitRecommendations.size)
}
