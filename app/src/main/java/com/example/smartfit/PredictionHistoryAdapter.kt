package com.example.smartfit

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.example.smartfit.databinding.ItemPredictionHistoryBinding
import com.example.smartfit.network.PredictionHistory
import com.example.smartfit.network.RetrofitClient
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import com.google.gson.JsonObject
import com.google.firebase.auth.FirebaseAuth
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.MediaType.Companion.toMediaTypeOrNull

class PredictionHistoryAdapter(private val predictionHistoryList: MutableList<PredictionHistory>) :
    RecyclerView.Adapter<PredictionHistoryAdapter.PredictionHistoryViewHolder>() {

    inner class PredictionHistoryViewHolder(private val binding: ItemPredictionHistoryBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(predictionHistory: PredictionHistory) {
            binding.seasonalColorLabelTextView.text = predictionHistory.seasonal_color_label
            binding.seasonalDescriptionTextView.text = predictionHistory.seasonal_description
            binding.timestampTextView.text = predictionHistory.timestamp
            binding.clothingTypeTextView.text = formatClothingType(predictionHistory.clothing_type)

            val firstProduct = predictionHistory.amazon_products.firstOrNull()
            if (firstProduct != null) {
                Glide.with(binding.productImageView.context)
                    .load(firstProduct.pic)
                    .into(binding.productImageView)
            } else {
                binding.productImageView.visibility = View.GONE
            }

            binding.deleteButton.setOnClickListener {
                deletePredictionHistory(predictionHistory.prediction_key, adapterPosition)
            }
        }

        private fun deletePredictionHistory(predictionKey: String, position: Int) {
            val uid = FirebaseAuth.getInstance().currentUser?.uid ?: return

            val uidRequestBody = RequestBody.create("multipart/form-data".toMediaTypeOrNull(), uid)
            val predictionKeyRequestBody = RequestBody.create("multipart/form-data".toMediaTypeOrNull(), predictionKey)

            val call = RetrofitClient.instance.deletePredictionHistory(uidRequestBody, predictionKeyRequestBody)

            call.enqueue(object : Callback<JsonObject> {
                override fun onResponse(call: Call<JsonObject>, response: Response<JsonObject>) {
                    if (response.isSuccessful) {
                        Toast.makeText(binding.root.context, "Deleted successfully", Toast.LENGTH_SHORT).show()
                        predictionHistoryList.removeAt(position)
                        notifyItemRemoved(position)
                    } else {
                        Toast.makeText(binding.root.context, "Failed to delete", Toast.LENGTH_SHORT).show()
                    }
                }

                override fun onFailure(call: Call<JsonObject>, t: Throwable) {
                    Toast.makeText(binding.root.context, "Error: ${t.message}", Toast.LENGTH_SHORT).show()
                }
            })
        }

        private fun formatClothingType(clothingType: String): String {
            return clothingType.split("-").joinToString(" ") { it.capitalize() }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): PredictionHistoryViewHolder {
        val binding = ItemPredictionHistoryBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return PredictionHistoryViewHolder(binding)
    }

    override fun onBindViewHolder(holder: PredictionHistoryViewHolder, position: Int) {
        holder.bind(predictionHistoryList[position])
    }

    override fun getItemCount(): Int {
        return predictionHistoryList.size
    }
}
