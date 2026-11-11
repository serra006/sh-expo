package com.serra.shexpo;

import android.app.Activity;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.CalendarContract;
import android.view.View;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

public class MainActivity extends Activity {

    public static final String CH_ID = "expo_remind";
    private static final int REQ_NOTIF = 1001;

    private WebView web;
    private boolean usedFallback = false;
    private boolean firstLoad = true;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            getWindow().setStatusBarColor(Color.parseColor("#0A0C0F"));
            getWindow().setNavigationBarColor(Color.parseColor("#0A0C0F"));
        } catch (Throwable ignored) {
        }
        createChannel();

        web = new WebView(this);
        web.setBackgroundColor(Color.parseColor("#0A0C0F"));
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(false);
        s.setDatabaseEnabled(true);
        s.setSupportZoom(false);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setTextZoom(100);
        web.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                if (!firstLoad) return;
                firstLoad = false;
                // 自检：首屏时间轴应当渲染出卡片。若为 0，说明页面脚本没跑起来，退回 file:// 再试一次。
                view.evaluateJavascript("(document.querySelectorAll('.card').length||0)",
                        new ValueCallback<String>() {
                            @Override
                            public void onReceiveValue(String v) {
                                int n = 0;
                                try {
                                    n = Integer.parseInt(v.replace("\"", "").trim());
                                } catch (Exception ignored) {
                                }
                                if (n == 0 && !usedFallback) {
                                    usedFallback = true;
                                    firstLoad = true;
                                    web.loadUrl("file:///android_asset/www/index.html");
                                }
                            }
                        });
            }
        });
        web.setWebChromeClient(new WebChromeClient());
        web.setLayerType(View.LAYER_TYPE_HARDWARE, null);
        web.addJavascriptInterface(new Bridge(), "SHExpo");
        // 长按不弹系统菜单，更像原生 App
        web.setOnLongClickListener(new View.OnLongClickListener() {
            @Override
            public boolean onLongClick(View v) {
                return true;
            }
        });
        setContentView(web);
        loadApp();
    }

    /**
     * 用 loadDataWithBaseURL 挂一个合成的 https 源，而不是 file://。
     * 原因：file:// 页面的 origin 是 "null"，部分 WebView 版本上 localStorage 会抛异常，
     * 导致收藏和提醒存不住。合成源能保证 DOM Storage 稳定可用。
     */
    private void loadApp() {
        String html = null;
        try {
            java.io.InputStream is = getAssets().open("www/index.html");
            java.io.ByteArrayOutputStream bo = new java.io.ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = is.read(buf)) > 0) bo.write(buf, 0, n);
            is.close();
            html = new String(bo.toByteArray(), "UTF-8");
        } catch (Throwable ignored) {
        }
        if (html != null && html.length() > 0) {
            web.loadDataWithBaseURL("https://shexpo.local/", html, "text/html", "utf-8", null);
        } else {
            web.loadUrl("file:///android_asset/www/index.html");
        }
    }

    private void createChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
            if (nm == null) return;
            NotificationChannel ch = new NotificationChannel(
                    CH_ID, "展会提醒", NotificationManager.IMPORTANCE_HIGH);
            ch.setDescription("展会开展前的提醒");
            ch.enableVibration(true);
            nm.createNotificationChannel(ch);
        }
    }

    @Override
    public void onBackPressed() {
        if (web == null) {
            super.onBackPressed();
            return;
        }
        web.evaluateJavascript(
                "window.onAndroidBack?window.onAndroidBack():false",
                new ValueCallback<String>() {
                    @Override
                    public void onReceiveValue(String v) {
                        if (!"true".equals(v)) finish();
                    }
                });
    }

    @Override
    protected void onDestroy() {
        if (web != null) {
            web.removeJavascriptInterface("SHExpo");
            web.destroy();
            web = null;
        }
        super.onDestroy();
    }

    private void toastOnUi(final String msg) {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                Toast.makeText(MainActivity.this, msg, Toast.LENGTH_SHORT).show();
            }
        });
    }

    /** 暴露给网页的桥。方法都在 JS 线程被调用，涉及 UI 的要切回主线程。 */
    public class Bridge {

        @JavascriptInterface
        public boolean isApp() {
            return true;
        }

        @JavascriptInterface
        public String version() {
            return "1.3";
        }

        @JavascriptInterface
        public void toast(String msg) {
            toastOnUi(msg);
        }

        @JavascriptInterface
        public void copy(final String text) {
            if (text == null || text.length() == 0) return;
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    try {
                        android.content.ClipboardManager cm =
                                (android.content.ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
                        if (cm != null) {
                            cm.setPrimaryClip(
                                    android.content.ClipData.newPlainText("上海展会", text));
                        }
                    } catch (Throwable ignored) {
                    }
                }
            });
        }

        @JavascriptInterface
        public void openUrl(final String url) {
            if (url == null || url.length() == 0) return;
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    try {
                        startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
                    } catch (ActivityNotFoundException e) {
                        toastOnUi("没有可打开该链接的应用");
                    } catch (Throwable t) {
                        toastOnUi("打开链接失败");
                    }
                }
            });
        }

        @JavascriptInterface
        public String addCalendar(final String title, final String location,
                                  final String desc, final long startMs, final long endMs) {
            try {
                // 先探测有没有能处理插入事件的应用，避免 startActivity 抛异常后 UI 状态不一致
                Intent probe = new Intent(Intent.ACTION_INSERT)
                        .setData(CalendarContract.Events.CONTENT_URI);
                if (probe.resolveActivity(getPackageManager()) == null) return "fail";

                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        try {
                            Intent i = new Intent(Intent.ACTION_INSERT);
                            i.setData(CalendarContract.Events.CONTENT_URI);
                            i.putExtra(CalendarContract.Events.TITLE, title);
                            i.putExtra(CalendarContract.Events.EVENT_LOCATION, location);
                            i.putExtra(CalendarContract.Events.DESCRIPTION, desc);
                            i.putExtra(CalendarContract.EXTRA_EVENT_BEGIN_TIME, startMs);
                            i.putExtra(CalendarContract.EXTRA_EVENT_END_TIME, endMs);
                            startActivity(i);
                        } catch (Throwable t) {
                            toastOnUi("写入日历失败");
                        }
                    }
                });
                return "ok";
            } catch (Throwable t) {
                return "fail";
            }
        }

        @JavascriptInterface
        public String setReminder(String id, String title, String text, long triggerMs) {
            try {
                if (triggerMs <= System.currentTimeMillis()) return "fail";
                ReminderStore.save(MainActivity.this, id, triggerMs, title, text);
                return "ok";
            } catch (Throwable t) {
                return "fail";
            }
        }

        @JavascriptInterface
        public void cancelReminder(String id) {
            try {
                ReminderStore.remove(MainActivity.this, id);
            } catch (Throwable ignored) {
            }
        }

        @JavascriptInterface
        public String listReminders() {
            try {
                return ReminderStore.toJson(MainActivity.this);
            } catch (Throwable t) {
                return "[]";
            }
        }

        @JavascriptInterface
        public void requestNotifPermission() {
            if (Build.VERSION.SDK_INT >= 33) {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        if (checkSelfPermission("android.permission.POST_NOTIFICATIONS")
                                != PackageManager.PERMISSION_GRANTED) {
                            requestPermissions(
                                    new String[]{"android.permission.POST_NOTIFICATIONS"}, REQ_NOTIF);
                        }
                    }
                });
            }
        }

        /* ---------- 在线更新：本地缓存 + 原生 HTTP ----------
         * 不走 WebView 的 fetch：页面挂在合成源 https://shexpo.local/ 上，
         * 跨域请求在不同 WebView 版本上表现不一致。原生 HttpURLConnection
         * 没有 CORS 问题，还能统一控制超时和端点回退。 */

        private java.io.File cacheFile() {
            return new java.io.File(getFilesDir(), "latest.json");
        }

        @JavascriptInterface
        public String loadCache() {
            try {
                java.io.File f = cacheFile();
                if (!f.exists() || f.length() > 4 * 1024 * 1024) return "";
                byte[] b = new byte[(int) f.length()];
                java.io.FileInputStream in = new java.io.FileInputStream(f);
                int off = 0, n;
                while (off < b.length && (n = in.read(b, off, b.length - off)) > 0) off += n;
                in.close();
                return new String(b, 0, off, "UTF-8");
            } catch (Throwable t) {
                return "";
            }
        }

        @JavascriptInterface
        public boolean saveCache(String json) {
            if (json == null || json.length() < 100) return false;
            java.io.File tmp = new java.io.File(getFilesDir(), "latest.json.tmp");
            try {
                java.io.FileOutputStream out = new java.io.FileOutputStream(tmp);
                out.write(json.getBytes("UTF-8"));
                out.flush();
                out.close();
                return tmp.renameTo(cacheFile());
            } catch (Throwable t) {
                return false;
            }
        }

        @JavascriptInterface
        public void fetch(final String url, final String cb) {
            if (url == null || !url.startsWith("https://") || cb == null
                    || !cb.matches("[A-Za-z_][A-Za-z0-9_]*")) return;
            new Thread(new Runnable() {
                @Override
                public void run() {
                    String text = "";
                    java.net.HttpURLConnection conn = null;
                    try {
                        java.net.URL u = new java.net.URL(url);
                        conn = (java.net.HttpURLConnection) u.openConnection();
                        conn.setConnectTimeout(8000);
                        conn.setReadTimeout(12000);
                        conn.setRequestMethod("GET");
                        conn.setRequestProperty("Accept", "application/json");
                        conn.setUseCaches(false);
                        if (conn.getResponseCode() == 200) {
                            java.io.InputStream is = conn.getInputStream();
                            java.io.ByteArrayOutputStream bo = new java.io.ByteArrayOutputStream();
                            byte[] buf = new byte[8192];
                            int n;
                            while ((n = is.read(buf)) > 0) bo.write(buf, 0, n);
                            is.close();
                            text = new String(bo.toByteArray(), "UTF-8");
                        }
                    } catch (Throwable ignored) {
                    } finally {
                        if (conn != null) conn.disconnect();
                    }
                    deliver(cb, text);
                }
            }, "expo-fetch").start();
        }

        private void deliver(final String cb, final String text) {
            final String arg;
            try {
                arg = org.json.JSONObject.quote(text == null ? "" : text);
            } catch (Throwable t) {
                return;
            }
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    if (web == null) return;
                    web.evaluateJavascript("window." + cb + "(" + arg + ")", null);
                }
            });
        }
    }
}
