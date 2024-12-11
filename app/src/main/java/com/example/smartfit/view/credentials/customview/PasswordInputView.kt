package com.example.smartfit.view.credentials.customview

import android.content.Context
import android.text.Editable
import android.text.InputFilter
import android.text.TextWatcher
import android.util.AttributeSet
import android.view.LayoutInflater
import android.view.View
import android.widget.LinearLayout
import com.example.smartfit.R
import com.example.smartfit.databinding.PasswordInputViewBinding

class PasswordInputView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : LinearLayout(context, attrs, defStyleAttr) {

    var binding: PasswordInputViewBinding

    init {
        orientation = VERTICAL
        binding = PasswordInputViewBinding.inflate(LayoutInflater.from(context), this, true)

        // Batasi input maksimal 6 karakter
        binding.passwordEditText.filters = arrayOf(InputFilter.LengthFilter(6))

        // Add TextWatcher for Password Validation
        binding.passwordEditText.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}

            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                validatePassword(s.toString())
            }

            override fun afterTextChanged(s: Editable?) {}
        })
    }

    private fun validatePassword(password: String) {
        if (password.length == 6) {
            binding.errorTextView.visibility = View.GONE
            binding.warningIcon.visibility = View.GONE // Sembunyikan ikon peringatan
        } else if (password.length < 6) {
            binding.errorTextView.visibility = View.VISIBLE
            binding.errorTextView.text = context.getString(R.string.tv_invalid_password_format_edt)
            binding.warningIcon.visibility = View.VISIBLE // Tampilkan ikon peringatan
        }
    }

    fun isPasswordValid(): Boolean {
        val password = binding.passwordEditText.text.toString()
        return password.length == 6
    }

    fun getText(): String {
        return binding.passwordEditText.text.toString()
    }
}
