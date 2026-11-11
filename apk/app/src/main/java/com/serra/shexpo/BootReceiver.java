package com.serra.shexpo;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** 重启后闹钟会被系统清空，需要重新登记。 */
public class BootReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context c, Intent i) {
        String a = i == null ? null : i.getAction();
        if (Intent.ACTION_BOOT_COMPLETED.equals(a)
                || "android.intent.action.QUICKBOOT_POWERON".equals(a)
                || Intent.ACTION_MY_PACKAGE_REPLACED.equals(a)) {
            try {
                ReminderStore.rescheduleAll(c);
            } catch (Throwable ignored) {
            }
        }
    }
}
