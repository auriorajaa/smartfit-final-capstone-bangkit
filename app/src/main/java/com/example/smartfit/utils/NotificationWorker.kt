package com.example.smartfit.utils

import android.content.Context
import androidx.work.Worker
import androidx.work.WorkerParameters
import com.example.smartfit.R

class NotificationWorker(appContext: Context, workerParams: WorkerParameters) :
    Worker(appContext, workerParams) {

    override fun doWork(): Result {
        val notificationTitle = applicationContext.getString(R.string.notification_title)
        val notificationMessage = applicationContext.getString(R.string.notification_message)

        NotificationHelper.sendNotification(
            applicationContext,
            notificationTitle,
            notificationMessage
        )

        // Simpan waktu notifikasi terakhir
        val sharedPreferences = applicationContext.getSharedPreferences("NotificationPrefs", Context.MODE_PRIVATE)
        with(sharedPreferences.edit()) {
            putLong("lastNotificationTime", System.currentTimeMillis())
            apply()
        }

        return Result.success()
    }
}
