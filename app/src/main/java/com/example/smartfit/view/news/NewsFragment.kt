package com.example.smartfit.view.news

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.smartfit.BuildConfig
import com.example.smartfit.data.remote.response.Article
import com.example.smartfit.data.remote.response.NewsResponse
import com.example.smartfit.data.remote.retrofit.NewsApiService
import com.example.smartfit.data.remote.retrofit.NewsRetrofitClient
import com.example.smartfit.databinding.FragmentNewsBinding
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class NewsFragment : Fragment() {

    private var _binding: FragmentNewsBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        _binding = FragmentNewsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.rvNews.layoutManager = LinearLayoutManager(requireContext())

        fetchNews()
    }

    private fun fetchNews() {
        binding.progressBar2.visibility = View.VISIBLE
        binding.rvNews.visibility = View.GONE

        val newsApiService = NewsRetrofitClient.instance.create(NewsApiService::class.java)
        val call = newsApiService.getNews(
            query = "fashion",
            from = "2024-11-25",
            to = "2024-12-15",
            sortBy = "relevance",
            apiKey = BuildConfig.NEWS_API_KEY
        )

        call.enqueue(object : Callback<NewsResponse> {
            override fun onResponse(call: Call<NewsResponse>, response: Response<NewsResponse>) {
                if (_binding != null) {
                    binding.progressBar2.visibility = View.GONE

                    if (response.isSuccessful) {
                        response.body()?.let { newsResponse ->
                            Log.d("NewsFragment", "News articles received: ${newsResponse.articles.size}")
                            binding.rvNews.visibility = View.VISIBLE
                            displayNews(newsResponse.articles)
                        } ?: run {
                            Log.e("NewsFragment", "Empty response body")
                        }
                    } else {
                        Log.e("NewsFragment", "Request failed with response code: ${response.code()}")
                    }
                }
            }

            override fun onFailure(call: Call<NewsResponse>, t: Throwable) {
                if (_binding != null) { // Pastikan binding tidak null sebelum mengakses
                    binding.progressBar2.visibility = View.GONE
                }
                Log.e("NewsFragment", "Request failed", t)
            }
        })
    }

    private fun displayNews(articles: List<Article>) {
        if (_binding != null) {
            val newsAdapter = NewsAdapter(articles) { article ->
                val intent = Intent(Intent.ACTION_VIEW, Uri.parse(article.url))
                startActivity(intent)
            }
            binding.rvNews.adapter = newsAdapter
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
