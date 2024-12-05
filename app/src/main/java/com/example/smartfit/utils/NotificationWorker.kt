package com.example.smartfit.utils

import android.content.Context
import androidx.work.Worker
import androidx.work.WorkerParameters

class NotificationWorker(appContext: Context, workerParams: WorkerParameters) :
    Worker(appContext, workerParams) {

    override fun doWork(): Result {
        NotificationHelper.sendNotification(
            applicationContext,
            "SmartFit Reminder",
            "Don't forget to check out the latest fashion trends on SmartFit!"
        )
        return Result.success()
    }
}
