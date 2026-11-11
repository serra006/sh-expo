package com.serra.shexpo;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Map;

/** 提醒的持久化与闹钟调度。存储格式：每个提醒一条 key，值为 JSON。 */
public final class ReminderStore {

    private static final String PREF = "reminders";
    private static final String PFX = "r_";
    public static final String ACTION = "com.serra.shexpo.REMIND";

    private ReminderStore() {
    }

    private static SharedPreferences sp(Context c) {
        return c.getSharedPreferences(PREF, Context.MODE_PRIVATE);
    }

    public static void save(Context c, String id, long t, String title, String text) {
        try {
            JSONObject o = new JSONObject();
            o.put("id", id);
            o.put("t", t);
            o.put("title", title == null ? "" : title);
            o.put("text", text == null ? "" : text);
            sp(c).edit().putString(PFX + id, o.toString()).apply();
        } catch (Exception ignored) {
        }
        schedule(c, id, t, title, text);
    }

    public static void remove(Context c, String id) {
        sp(c).edit().remove(PFX + id).apply();
        cancel(c, id);
    }

    /** 通知已弹出，清掉记录（对应「已设提醒」列表） */
    public static void markFired(Context c, String id) {
        sp(c).edit().remove(PFX + id).apply();
    }

    public static String toJson(Context c) {
        JSONArray arr = new JSONArray();
        for (Map.Entry<String, ?> e : sp(c).getAll().entrySet()) {
            try {
                arr.put(new JSONObject(String.valueOf(e.getValue())));
            } catch (Exception ignored) {
            }
        }
        return arr.toString();
    }

    /** 开机后重新登记所有未到期的提醒（闹钟在重启后会被清空） */
    public static void rescheduleAll(Context c) {
        long now = System.currentTimeMillis();
        for (Map.Entry<String, ?> e : sp(c).getAll().entrySet()) {
            try {
                JSONObject o = new JSONObject(String.valueOf(e.getValue()));
                long t = o.optLong("t");
                if (t > now) {
                    schedule(c, o.optString("id"), t, o.optString("title"), o.optString("text"));
                } else {
                    sp(c).edit().remove(e.getKey()).apply();
                }
            } catch (Exception ignored) {
            }
        }
    }

    public static void schedule(Context c, String id, long t, String title, String text) {
        AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
        if (am == null) return;
        PendingIntent pi = pi(c, id, title, text);
        try {
            if (Build.VERSION.SDK_INT >= 23) {
                am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, t, pi);
            } else {
                am.setExact(AlarmManager.RTC_WAKEUP, t, pi);
            }
        } catch (SecurityException se) {
            // 未授予精确闹钟权限时退化为非精确，误差通常在几分钟内
            am.set(AlarmManager.RTC_WAKEUP, t, pi);
        } catch (Throwable ignored) {
        }
    }

    public static void cancel(Context c, String id) {
        AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
        if (am == null) return;
        try {
            am.cancel(pi(c, id, null, null));
        } catch (Throwable ignored) {
        }
    }

    private static PendingIntent pi(Context c, String id, String title, String text) {
        Intent i = new Intent(c, ReminderReceiver.class);
        i.setAction(ACTION);
        i.putExtra("id", id);
        if (title != null) i.putExtra("title", title);
        if (text != null) i.putExtra("text", text);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= 23) flags |= PendingIntent.FLAG_IMMUTABLE;
        return PendingIntent.getBroadcast(c, reqCode(id), i, flags);
    }

    private static int reqCode(String id) {
        return id == null ? 0 : (id.hashCode() & 0x7fffffff);
    }
}
