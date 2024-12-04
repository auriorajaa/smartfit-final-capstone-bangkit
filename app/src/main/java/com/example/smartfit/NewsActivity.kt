package com.example.smartfit

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.smartfit.databinding.ActivityNewsBinding
import com.example.smartfit.network.Article
import com.example.smartfit.network.NewsApiService
import com.example.smartfit.network.NewsRetrofitClient
import com.example.smartfit.network.NewsResponse
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class NewsActivity : AppCompatActivity() {

    private lateinit var binding: ActivityNewsBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityNewsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.newsRecyclerView.layoutManager = LinearLayoutManager(this)

        fetchNews()
    }

    private fun fetchNews() {
        val newsApiService = NewsRetrofitClient.instance.create(NewsApiService::class.java)
        val call = newsApiService.getNews(
            query = "fashion",
            from = "2024-11-20",
            to = "2024-12-10",
            sortBy = "relevance",
            apiKey = BuildConfig.NEWS_API_KEY
        )

        call.enqueue(object : Callback<NewsResponse> {
            override fun onResponse(call: Call<NewsResponse>, response: Response<NewsResponse>) {
                if (response.isSuccessful) {
                    response.body()?.let {
                        Log.d("NewsActivity", "News articles received: ${it.articles.size}")
                        displayNews(it.articles)
                    } ?: run {
                        Log.e("NewsActivity", "Empty response body")
                    }
                } else {
                    Log.e("NewsActivity", "Request failed with response code: ${response.code()}")
                }
            }

            override fun onFailure(call: Call<NewsResponse>, t: Throwable) {
                Log.e("NewsActivity", "Request failed", t)
            }
        })
    }

    private fun displayNews(articles: List<Article>) {
        val newsAdapter = NewsAdapter(articles) { article ->
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(article.url))
            startActivity(intent)
        }
        binding.newsRecyclerView.adapter = newsAdapter
    }
}
