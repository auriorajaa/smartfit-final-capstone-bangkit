package com.example.smartfit.view.credentials.customview

import android.content.Context
import android.text.Editable
import android.text.TextWatcher
import android.util.AttributeSet
import android.util.Patterns
import android.view.LayoutInflater
import android.view.View
import android.widget.LinearLayout
import com.example.smartfit.databinding.EmailInputViewBinding

class EmailInputView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : LinearLayout(context, attrs, defStyleAttr) {

    private var binding: EmailInputViewBinding

    init {
        orientation = VERTICAL
        binding = EmailInputViewBinding.inflate(LayoutInflater.from(context), this, true)

        // Add TextWatcher for Email Validation
        binding.emailEditText.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                validateEmail(s.toString())
            }

            override fun afterTextChanged(s: Editable?) {}
        })
    }

    private fun validateEmail(email: String) {
        if (email.isEmpty() || Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
            binding.errorTextView.visibility = View.GONE
            binding.warningIcon.visibility = View.GONE // Sembunyikan ikon peringatan
        } else {
            binding.errorTextView.visibility = View.VISIBLE
            binding.errorTextView.text = "Format email tidak valid"
            binding.warningIcon.visibility = View.VISIBLE // Tampilkan ikon peringatan
        }
    }

    fun isEmailValid(): Boolean {
        val email = binding.emailEditText.text.toString()
        return email.isNotEmpty() && Patterns.EMAIL_ADDRESS.matcher(email).matches()
    }

    fun getText(): String {
        return binding.emailEditText.text.toString()
    }
}
