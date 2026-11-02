#!/usr/bin/env bash
# Builds and signs the launcher with the Android SDK tools, without Gradle.
# Needs a JDK (11+) and the SDK build-tools and a platform. Leaves build/launcher.apk.
set -euo pipefail
cd "$(dirname "$0")"
SDK=${ANDROID_HOME:-$HOME/Library/Android/sdk}
[ -d "$SDK" ] || SDK=$HOME/Android/Sdk
BT=$SDK/build-tools/$(ls "$SDK/build-tools" | sort -V | tail -1)
JAR=$SDK/platforms/$(ls "$SDK/platforms" | sort -V | tail -1)/android.jar
KEYSTORE=${KEYSTORE:-$HOME/.android/debug.keystore}

if [ ! -f "$KEYSTORE" ]; then
  mkdir -p "$(dirname "$KEYSTORE")"
  keytool -genkeypair -keystore "$KEYSTORE" -storepass android -keypass android \
    -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Android Debug,O=Android,C=US"
fi

rm -rf build && mkdir -p build/classes build/dex
"$BT/aapt2" link --manifest AndroidManifest.xml -I "$JAR" -o build/no_code.apk
find src -name '*.java' -print0 | xargs -0 javac -source 11 -target 11 -nowarn -Xlint:-options \
  -classpath "$JAR" -d build/classes
find build/classes -name '*.class' -print0 | xargs -0 "$BT/d8" --min-api 29 --lib "$JAR" --output build/dex
cp build/no_code.apk build/unsigned.apk
(cd build/dex && zip -q ../unsigned.apk classes.dex)
"$BT/zipalign" -f 4 build/unsigned.apk build/aligned.apk
# To update an installed copy, sign with the same key.
"$BT/apksigner" sign --ks "$KEYSTORE" --ks-pass pass:android --key-pass pass:android \
  --ks-key-alias androiddebugkey --out build/launcher.apk build/aligned.apk
echo "Done: $(pwd)/build/launcher.apk"
