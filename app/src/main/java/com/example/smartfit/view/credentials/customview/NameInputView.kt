package com.example.smartfit.view.credentials.customview

import android.content.Context
import android.text.Editable
import android.text.TextWatcher
import android.util.AttributeSet
import android.widget.LinearLayout
import android.view.LayoutInflater
import android.view.View
import androidx.core.widget.addTextChangedListener
import com.example.smartfit.databinding.NameInputViewBinding

class NameInputView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : LinearLayout(context, attrs, defStyleAttr) {

    var binding: NameInputViewBinding

    init {
        orientation = VERTICAL
        binding = NameInputViewBinding.inflate(LayoutInflater.from(context), this, true)

        // Add TextWatcher for Name Validation
        binding.nameEditText.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                validateName(s.toString())
            }
            override fun afterTextChanged(s: Editable?) {}
        })
    }

    private fun validateName(name: String) {
        if (name.length >= 4) {
            binding.errorTextView.visibility = View.GONE
            binding.warningIcon.visibility = View.GONE // Sembunyikan ikon peringatan
        } else {
            binding.errorTextView.visibility = View.VISIBLE
            binding.errorTextView.text = "Nama harus memiliki minimal 4 karakter"
            binding.warningIcon.visibility = View.VISIBLE // Tampilkan ikon peringatan
        }
    }

    fun isNameValid(): Boolean {
        val name = binding.nameEditText.text.toString()
        return name.length >= 4
    }
}
