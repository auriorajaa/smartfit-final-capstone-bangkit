package com.example.smartfit

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.example.smartfit.databinding.ItemAmazonProductBinding
import com.example.smartfit.network.AmazonProduct

class AmazonProductAdapter(private val context: Context, private val products: List<AmazonProduct>) :
    RecyclerView.Adapter<AmazonProductAdapter.ViewHolder>() {

    inner class ViewHolder(val binding: ItemAmazonProductBinding) : RecyclerView.ViewHolder(binding.root) {
        init {
            binding.root.setOnClickListener {
                val position = adapterPosition
                if (position != RecyclerView.NO_POSITION) {
                    val product = products[position]
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(product.detail_url))
                    context.startActivity(intent)
                }
            }
        }

        fun bind(product: AmazonProduct) {
            Glide.with(context).load(product.pic).into(binding.productImage)
            binding.productTitle.visibility = View.GONE
            binding.productDescription.visibility = View.GONE
            binding.productPrice.visibility = View.GONE
            binding.productSalesVolume.visibility = View.GONE
            binding.productDelivery.visibility = View.GONE
            binding.productPrime.visibility = View.GONE
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemAmazonProductBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(products[position])
    }

    override fun getItemCount(): Int = products.size
}
