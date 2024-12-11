package com.example.smartfit.utils

import android.content.Context
import android.view.LayoutInflater
import android.view.View
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import com.example.smartfit.R
import com.google.android.material.button.MaterialButton

fun showUniversalDialog(
    context: Context,
    title: String,
    message: String,
    positiveButtonText: String,
    negativeButtonText: String?,
    positiveAction: (() -> Unit)?,
    negativeAction: (() -> Unit)?
) {
    val dialogView = LayoutInflater.from(context).inflate(R.layout.dialog_universal, null)
    val builder = AlertDialog.Builder(context)
    builder.setView(dialogView)

    val dialog = builder.create()

    dialogView.findViewById<TextView>(R.id.dialog_title).text = title
    dialogView.findViewById<TextView>(R.id.dialog_message).text = message

    val positiveButton = dialogView.findViewById<MaterialButton>(R.id.dialog_positive_button)
    val negativeButton = dialogView.findViewById<MaterialButton>(R.id.dialog_negative_button)

    positiveButton.text = positiveButtonText
    positiveButton.setOnClickListener {
        dialog.dismiss()
        positiveAction?.invoke()
    }

    if (negativeButtonText != null) {
        negativeButton.text = negativeButtonText
        negativeButton.setOnClickListener {
            dialog.dismiss()
            negativeAction?.invoke()
        }
    } else {
        negativeButton.visibility = View.GONE
    }

    dialog.show()
}
