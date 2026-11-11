import os
import zipfile

ROOT = r"C:/Users/se/WorkBuddy/2026-11-04-14-55-47/sh-expo/apk"
src = os.path.join(ROOT, "build", "base_noassets.apk")
dst = os.path.join(ROOT, "build", "withassets.apk")
www = os.path.join(ROOT, "app", "src", "main", "assets", "www")

zin = zipfile.ZipFile(src)
zout = zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED)
for it in zin.infolist():
    zout.writestr(it, zin.read(it.filename))
for dirpath, _, files in os.walk(www):
    for fn in files:
        full = os.path.join(dirpath, fn)
        arc = "assets/www/" + os.path.relpath(full, www).replace(os.sep, "/")
        zout.write(full, arc)
        print(" ", arc, "%.1f KB" % (os.path.getsize(full) / 1024.0))
zout.close()
zin.close()
print("OK -> withassets.apk")
