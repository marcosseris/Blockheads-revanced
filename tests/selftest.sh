#!/usr/bin/env bash
# End-to-end test on a synthetic legacy APK (no game files needed).
set -euo pipefail
cd "$(dirname "$0")/.."
T=work/selftest
rm -rf "$T" && mkdir -p "$T/src/res/values" "$T/src/lib/armeabi-v7a"

cat > "$T/src/AndroidManifest.xml" <<'XML'
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.example.legacygame">
    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>
    <uses-permission android:name="android.permission.GET_TASKS"/>
    <application android:label="@string/app_name">
        <activity android:name=".Main">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
    </application>
</manifest>
XML
cat > "$T/src/res/values/strings.xml" <<'XML'
<?xml version="1.0" encoding="utf-8"?>
<resources><string name="app_name">Legacy Game</string></resources>
XML
cat > "$T/src/apktool.yml" <<'YML'
version: 2.10.0
apkFileName: legacy.apk
isFrameworkApk: false
usesFramework:
  ids:
  - 1
sdkInfo:
  minSdkVersion: '9'
  targetSdkVersion: '10'
packageInfo:
  forcedPackageId: 127
versionInfo:
  versionCode: '1'
  versionName: 1.0
doNotCompress:
- resources.arsc
YML
printf '\x7fELF-dummy' > "$T/src/lib/armeabi-v7a/libgame.so"

java -jar tools/apktool.jar b -q -f -o "$T/legacy.apk" "$T/src" >/dev/null
python3 patcher/patch.py "$T/legacy.apk" -o "$T/patched.apk" --target-sdk 31 \
  --keystore "$T/test.keystore" | tee "$T/log.txt"

java -jar tools/uber-apk-signer.jar --onlyVerify --apks "$T/patched.apk" | grep -q "VERIFY" 
java -jar tools/apktool.jar d -q -f -s -o "$T/check" "$T/patched.apk" >/dev/null
M="$T/check/AndroidManifest.xml"
fail() { echo "FAIL: $1"; exit 1; }
grep -Eq "targetSdkVersion: '?31'?" "$T/check/apktool.yml" || fail "targetSdk not raised"
grep -q 'android:exported="true"' "$M"                     || fail "exported missing"
grep -q 'usesCleartextTraffic="true"' "$M"                 || fail "cleartext missing"
grep -q 'requestLegacyExternalStorage="true"' "$M"         || fail "legacy storage missing"
grep -q 'extractNativeLibs="true"' "$M"                    || fail "extractNativeLibs missing"
grep -q 'GET_TASKS' "$M"                                   && fail "GET_TASKS not stripped"
grep -q '32-bit only' "$T/log.txt"                         || fail "ABI warning missing"
echo "SELFTEST PASSED"
