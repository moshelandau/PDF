package com.hatzolah.members

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class HatzolahApp : Application() {

    companion object {
        const val DISPATCH_CHANNEL_ID = "dispatch_notifications"
        const val TRACKING_CHANNEL_ID = "location_tracking"
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        val dispatchChannel = NotificationChannel(
            DISPATCH_CHANNEL_ID,
            "Dispatch Alerts",
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Incoming dispatch call notifications"
            setShowBadge(true)
            enableVibration(true)
            lockscreenVisibility = android.app.Notification.VISIBILITY_PUBLIC
        }

        val trackingChannel = NotificationChannel(
            TRACKING_CHANNEL_ID,
            "Location Tracking",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "Active call location tracking"
        }

        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(dispatchChannel)
        manager.createNotificationChannel(trackingChannel)
    }
}
