package com.example.smartfit.utils

//import android.app.NotificationChannel
//import android.app.NotificationManager
//import android.app.PendingIntent
//import android.content.Context
//import android.content.Intent
//import android.graphics.Color
//import android.os.Build
//import android.util.Log
//import androidx.core.app.NotificationCompat
//import androidx.core.app.NotificationManagerCompat
//import androidx.core.content.ContextCompat
//import com.example.smartfit.R
//
//object NotificationHelper {
//
//    private const val CHANNEL_ID = "smartfit_channel"
//    private const val CHANNEL_NAME = "SmartFit Notifications"
//    private const val CHANNEL_DESC = "Notifications for SmartFit app"
//    private const val NOTIFICATION_ID = 1
//
//    fun createNotificationChannel(context: Context) {
//        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
//            val channel = NotificationChannel(
//                CHANNEL_ID,
//                CHANNEL_NAME,
//                NotificationManager.IMPORTANCE_DEFAULT
//            ).apply {
//                description = CHANNEL_DESC
//                enableLights(true)
//                lightColor = Color.BLUE
//                enableVibration(true)
//            }
//            val notificationManager: NotificationManager =
//                context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
//            notificationManager.createNotificationChannel(channel)
//        }
//    }
//
//    fun sendNotification(context: Context, title: String, message: String) {
//        val notificationManager = NotificationManagerCompat.from(context)
//
//        if (ContextCompat.checkSelfPermission(context, "android.permission.POST_NOTIFICATIONS") == 0) {
//            val intent = Intent(context, MainActivity::class.java).apply {
//                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
//            }
//            val pendingIntent: PendingIntent = PendingIntent.getActivity(context, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT)
//
//            val notification = NotificationCompat.Builder(context, CHANNEL_ID)
//                .setSmallIcon(R.drawable.ic_notification)
//                .setContentTitle(title)
//                .setContentText(message)
//                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
//                .setContentIntent(pendingIntent)
//                .setAutoCancel(true)
//                .build()
//
//            notificationManager.notify(NOTIFICATION_ID, notification)
//        } else {
//            Log.e("NotificationHelper", "Permission for notifications not granted")
//        }
//    }
//}
