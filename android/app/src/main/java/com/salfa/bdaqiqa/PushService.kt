package com.salfa.bdaqiqa

import android.app.PendingIntent
import android.content.Intent
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

/** Shows "new post" notifications even when the app is open. */
class PushService : FirebaseMessagingService() {

    companion object {
        const val CHANNEL_ID = "new_posts"
        const val TOPIC = "new_posts"
    }

    override fun onMessageReceived(msg: RemoteMessage) {
        val title = msg.notification?.title ?: msg.data["title"] ?: getString(R.string.app_name)
        val body = msg.notification?.body ?: msg.data["body"] ?: ""
        val url = msg.data["url"]

        val open = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            if (url != null) putExtra("url", url)
        }
        val pi = PendingIntent.getActivity(
            this, System.currentTimeMillis().toInt(), open,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val n = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setColor(ContextCompat.getColor(this, R.color.brand_orange))
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(pi)
            .build()
        try {
            NotificationManagerCompat.from(this).notify(System.currentTimeMillis().toInt(), n)
        } catch (_: SecurityException) { /* notification permission not granted */ }
    }

    override fun onNewToken(token: String) {
        // We use the "new_posts" topic, so no per-device token storage is needed.
    }
}
