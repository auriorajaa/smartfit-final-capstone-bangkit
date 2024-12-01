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
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemAmazonProductBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val product = products[position]
        with(holder.binding) {
            Glide.with(context).load(product.pic).into(productImage)
            productTitle.text = product.title
            productDescription.text = product.description
            productPrice.text = product.price ?: "Price not available"
            productSalesVolume.text = product.sales_volume
            productDelivery.text = product.delivery
            productPrime.visibility = if (product.is_prime) View.VISIBLE else View.GONE
            productPrime.text = if (product.is_prime) "Prime" else ""
        }
    }

    override fun getItemCount(): Int = products.size
}
