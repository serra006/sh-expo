package com.serra.shexpo;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

/** 到点弹通知。 */
public class ReminderReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context c, Intent i) {
        String id = i.getStringExtra("id");
        String title = i.getStringExtra("title");
        String text = i.getStringExtra("text");
        if (title == null || title.length() == 0) title = "展会提醒";

        NotificationManager nm = (NotificationManager) c.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null) return;

        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel ch = new NotificationChannel(
                    MainActivity.CH_ID, "展会提醒", NotificationManager.IMPORTANCE_HIGH);
            ch.setDescription("展会开展前的提醒");
            ch.enableVibration(true);
            nm.createNotificationChannel(ch);
        }

        Intent open = new Intent(c, MainActivity.class);
        open.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        int pf = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= 23) pf |= PendingIntent.FLAG_IMMUTABLE;
        PendingIntent cont = PendingIntent.getActivity(
                c, id == null ? 0 : (id.hashCode() & 0x7fffffff), open, pf);

        Notification.Builder b;
        if (Build.VERSION.SDK_INT >= 26) {
            b = new Notification.Builder(c, MainActivity.CH_ID);
        } else {
            b = new Notification.Builder(c);
            b.setPriority(Notification.PRIORITY_HIGH);
            b.setDefaults(Notification.DEFAULT_ALL);
        }
        b.setSmallIcon(R.drawable.ic_stat_bell)
                .setContentTitle(title)
                .setContentText(text == null ? "" : text)
                .setStyle(new Notification.BigTextStyle().bigText(text == null ? "" : text))
                .setAutoCancel(true)
                .setContentIntent(cont);

        try {
            nm.notify(id == null ? 1 : (id.hashCode() & 0xffff), b.build());
        } catch (Throwable ignored) {
        }

        if (id != null) ReminderStore.markFired(c, id);
    }
}
