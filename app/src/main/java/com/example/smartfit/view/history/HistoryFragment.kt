package com.example.smartfit.view.history

import android.os.Build
import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.annotation.RequiresApi
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.smartfit.data.remote.response.AmazonProduct
import com.example.smartfit.data.remote.response.ColorPalette
import com.example.smartfit.data.remote.response.OutfitRecommendation
import com.example.smartfit.data.remote.response.PredictionHistory
import com.example.smartfit.data.remote.retrofit.RetrofitClient
import com.example.smartfit.databinding.FragmentHistoryBinding
import com.google.firebase.auth.FirebaseAuth
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import com.google.gson.JsonObject

class HistoryFragment : Fragment() {

    private var _binding: FragmentHistoryBinding? = null
    private val binding get() = _binding!!
    private lateinit var adapter: PredictionHistoryAdapter

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        _binding = FragmentHistoryBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.historyRecyclerView.layoutManager = LinearLayoutManager(requireContext())

        fetchPredictionHistory()
    }

    private fun fetchPredictionHistory() {
        val uid = FirebaseAuth.getInstance().currentUser?.uid ?: return

        RetrofitClient.instance.getPredictionHistoryList(uid).enqueue(object : Callback<JsonObject> {
            @RequiresApi(Build.VERSION_CODES.O)
            override fun onResponse(call: Call<JsonObject>, response: Response<JsonObject>) {
                Log.d("HistoryFragment", "onResponse: ${response.raw()}")
                if (response.isSuccessful) {
                    val predictionHistoryJson = response.body()?.getAsJsonObject("prediction_data")
                    Log.d("HistoryFragment", "predictionHistoryJson: $predictionHistoryJson")
                    if (predictionHistoryJson != null) {
                        val predictionHistoryList = mutableListOf<PredictionHistory>()
                        for ((key, value) in predictionHistoryJson.entrySet()) {
                            val timestamp = value.asJsonObject.get("timestamp")?.asString ?: ""
                            val amazonProductsJson = value.asJsonObject.getAsJsonArray("amazon_products")
                            val amazonProducts = amazonProductsJson?.mapNotNull { product ->
                                val productObj = product.asJsonObject
                                AmazonProduct(
                                    asin = productObj.get("asin")?.asString ?: "",
                                    delivery = productObj.get("delivery")?.asString ?: "",
                                    description = productObj.get("description")?.asString ?: "",
                                    detail_url = productObj.get("detail_url")?.asString ?: "",
                                    is_prime = productObj.get("is_prime")?.asBoolean ?: false,
                                    pic = productObj.get("pic")?.asString ?: "",
                                    price = productObj.get("price")?.asString,
                                    sales_volume = productObj.get("sales_volume")?.asString ?: "",
                                    title = productObj.get("title")?.asString ?: ""
                                )
                            } ?: listOf()
                            val predictionHistory = PredictionHistory(
                                prediction_key = key,
                                amazon_products = amazonProducts,
                                clothing_type = value.asJsonObject.get("clothing_type")?.asString ?: "",
                                color_palette = ColorPalette(
                                    dark_colors = value.asJsonObject.getAsJsonObject("color_palette").getAsJsonArray("dark_colors").map { it.asString },
                                    light_colors = value.asJsonObject.getAsJsonObject("color_palette").getAsJsonArray("light_colors").map { it.asString }
                                ),
                                outfit_recommendations = value.asJsonObject.getAsJsonArray("outfit_recommendations")?.mapNotNull { recommendation ->
                                    val recommendationObj = recommendation.asJsonObject
                                    OutfitRecommendation(
                                        item = recommendationObj.get("item")?.asString ?: "",
                                        description = recommendationObj.get("description")?.asString ?: ""
                                    )
                                } ?: listOf(),
                                seasonal_color_label = value.asJsonObject.get("seasonal_color_label")?.asString ?: "",
                                seasonal_description = value.asJsonObject.get("seasonal_description")?.asString ?: "",
                                seasonal_probability = value.asJsonObject.get("seasonal_probability")?.asDouble ?: 0.0,
                                skin_tone_hex = value.asJsonObject.get("skin_tone_hex")?.asString ?: "",
                                skin_tone_label = value.asJsonObject.get("skin_tone_label")?.asString ?: "",
                                skin_tone_probability = value.asJsonObject.get("skin_tone_probability")?.asDouble ?: 0.0,
                                timestamp = timestamp,
                                user_uid = value.asJsonObject.get("user_uid")?.asString ?: ""
                            )
                            predictionHistoryList.add(predictionHistory)
                        }

                        // Reverse the list to show the latest data at the top
                        predictionHistoryList.reverse()

                        if (predictionHistoryList.isNotEmpty()) {
                            adapter = PredictionHistoryAdapter(predictionHistoryList)
                            binding.historyRecyclerView.adapter = adapter
                            binding.historyRecyclerView.visibility = View.VISIBLE
                            binding.emptyView.visibility = View.GONE
                        } else {
                            binding.historyRecyclerView.visibility = View.GONE
                            binding.emptyView.visibility = View.VISIBLE
                        }
                    } else {
                        binding.historyRecyclerView.visibility = View.GONE
                        binding.emptyView.visibility = View.VISIBLE
                        Toast.makeText(requireContext(), "No history found", Toast.LENGTH_SHORT).show()
                    }
                } else {
                    binding.historyRecyclerView.visibility = View.GONE
                    binding.emptyView.visibility = View.VISIBLE
                    Toast.makeText(requireContext(), "Failed to fetch history", Toast.LENGTH_SHORT).show()
                }
            }

            override fun onFailure(call: Call<JsonObject>, t: Throwable) {
                Log.e("HistoryFragment", "onFailure: ${t.message}", t)
                binding.historyRecyclerView.visibility = View.GONE
                binding.emptyView.visibility = View.VISIBLE
                Toast.makeText(requireContext(), "Error: ${t.message}", Toast.LENGTH_SHORT).show()
            }
        })
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
