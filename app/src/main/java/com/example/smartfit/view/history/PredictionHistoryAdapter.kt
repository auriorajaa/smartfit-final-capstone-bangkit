package com.example.smartfit.view.history

import android.app.AlertDialog
import android.content.Intent
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.example.smartfit.data.remote.response.PredictionHistory
import com.example.smartfit.data.remote.retrofit.RetrofitClient
import com.example.smartfit.databinding.ItemPredictionHistoryBinding
import com.example.smartfit.view.detection.result.DetailActivity
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import com.google.gson.JsonObject
import com.google.firebase.auth.FirebaseAuth
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

            // Set up item click listener to open DetailActivity
            binding.root.setOnClickListener {
                val context = binding.root.context
                val intent = Intent(context, DetailActivity::class.java).apply {
                    putExtra("PREDICTION_KEY", predictionHistory.prediction_key)
                    putExtra("USER_ID", predictionHistory.user_uid)
                }
                context.startActivity(intent)
            }

            binding.cvDeleteHistory.setOnClickListener {
                showDeleteConfirmationDialog(predictionHistory.prediction_key, adapterPosition)
            }
        }

        private fun showDeleteConfirmationDialog(predictionKey: String, position: Int) {
            val context = binding.root.context
            AlertDialog.Builder(context).apply {
                setTitle("Delete Confirmation")
                setMessage("Are you sure you want to delete this prediction history?")
                setPositiveButton("Yes") { _, _ ->
                    deletePredictionHistory(predictionKey, position)
                }
                setNegativeButton("No", null)
            }.create().show()
        }

        private fun deletePredictionHistory(predictionKey: String, position: Int) {
            val uid = FirebaseAuth.getInstance().currentUser?.uid ?: return

            val uidRequestBody = RequestBody.create("multipart/form-data".toMediaTypeOrNull(), uid)
            val predictionKeyRequestBody = RequestBody.create("multipart/form-data".toMediaTypeOrNull(), predictionKey)

            val call = RetrofitClient.instance.deletePredictionHistory(uidRequestBody, predictionKeyRequestBody)

            call.enqueue(object : Callback<JsonObject> {
                override fun onResponse(call: Call<JsonObject>, response: Response<JsonObject>) {
                    if (response.isSuccessful) {
                        Log.d("PredictionHistoryAdapter", "Delete successful: $response")
                        Toast.makeText(binding.root.context, "Deleted successfully", Toast.LENGTH_SHORT).show()
                        predictionHistoryList.removeAt(position)
                        notifyItemRemoved(position)
                        notifyItemRangeChanged(position, predictionHistoryList.size)
                    } else {
                        Log.e("PredictionHistoryAdapter", "Delete failed: ${response.errorBody()?.string()}")
                        Toast.makeText(binding.root.context, "Failed to delete", Toast.LENGTH_SHORT).show()
                    }
                }

                override fun onFailure(call: Call<JsonObject>, t: Throwable) {
                    Log.e("PredictionHistoryAdapter", "Delete error: ${t.message}", t)
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
