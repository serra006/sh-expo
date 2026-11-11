#!/bin/bash
# 上海展会 APK 构建脚本（手工流水线，无 Gradle）
# 用法: bash build_apk.sh [版本号]     例: bash build_apk.sh 1.0
#
# 关键注意（踩过的坑，别改回去）：
#   1. 不能用 aapt2 的 -A 参数打 assets —— Windows 上会写出反斜杠路径，
#      Android AssetManager 只认正斜杠，运行时报 ERR_FILE_NOT_FOUND。
#      assets 统一由 add_assets.py 用 Python zipfile 写入。
#   2. d8.bat / apksigner.bat 依赖 JAVA_HOME，必须指向 JDK（不是 JRE）。
set -e

VER="${1:-1.0}"
ROOT="C:/Users/se/WorkBuddy/2026-11-04-14-55-47/sh-expo/apk"
SDK="C:/Users/se/AppData/Local/Android/Sdk"
BT="$SDK/build-tools/36.1.0"
PLAT="$SDK/platforms/android-36/android.jar"
PY="C:/Users/se/AppData/Local/Programs/Python/Python311/python.exe"
KS="E:/3/apk/debug.keystore"

# 优先用这台机器上验证过的 E 盘 JDK。系统 JAVA_HOME 指向 G:\xxx\tools\jdk21 时，
# 它的 javac 往当前工作区写 class 会失败（写入 BootReceiver.class 报错），别被它带偏。
JDK="E:/3/jdk/jdk-21.0.12.1+1"
if [ ! -x "$JDK/bin/javac.exe" ]; then
  if [ -n "$JAVA_HOME" ] && [ -x "$JAVA_HOME/bin/javac.exe" ]; then
    JDK="$JAVA_HOME"
  else
    echo "找不到 JDK，请设置 JAVA_HOME"; exit 1
  fi
fi
export JAVA_HOME="$JDK"
export PATH="$JDK/bin:$PATH"

cd "$ROOT"

echo "==> 1/7 生成网页资源"
"$PY" build_www.py

echo "==> 2/7 编译资源"
# Windows 上删除目录或 class 文件后立刻让 javac 重建，会撞上 delete-pending /
# 文件占用（报 could not create parent directories 或直接写入失败）。
# javac 本来就覆盖同名 class，所以只建目录、不删任何东西。
mkdir -p build/gen build/classes/com/serra/shexpo
"$BT/aapt2.exe" compile --dir app/src/main/res -o build/res.zip

echo "==> 3/7 链接 APK（不含 assets）"
"$BT/aapt2.exe" link -o build/base_noassets.apk -I "$PLAT" \
  --manifest app/src/main/AndroidManifest.xml --java build/gen build/res.zip

echo "==> 4/7 编译 Java 并转 dex"
# Windows 版 javac 用相对路径 -d 时无法创建包目录（could not create parent directories），
# 必须给绝对的 Windows 风格路径。
"$JDK/bin/javac.exe" --release 11 -cp "$PLAT" -d "$ROOT/build/classes" \
  app/src/main/java/com/serra/shexpo/*.java build/gen/com/serra/shexpo/R.java
"$BT/d8.bat" --release --lib "$PLAT" --min-api 24 \
  --output build build/classes/com/serra/shexpo/*.class
cp -f build/classes.dex .
"$BT/aapt.exe" add build/base_noassets.apk classes.dex

echo "==> 5/7 写入 assets（正斜杠路径）"
"$PY" add_assets.py

echo "==> 6/7 对齐"
"$BT/zipalign.exe" -f 4 build/withassets.apk build/final_aligned.apk

echo "==> 7/7 签名"
"$BT/apksigner.bat" sign --ks "$(cygpath -w "$KS")" \
  --ks-pass pass:android --out "ShanghaiExpo-$VER.apk" build/final_aligned.apk

echo "==> 完成"
"$BT/aapt.exe" dump badging "ShanghaiExpo-$VER.apk" | head -4
ls -l "ShanghaiExpo-$VER.apk"
