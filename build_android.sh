#!/bin/bash
set -e

VERSION="2.3.9"
APK_SOURCE="build/farmasave/android/gradle/app/build/outputs/apk/debug/app-debug.apk"
APK_DEST="app-debug-v${VERSION}.apk"

echo "Building Farmasave v${VERSION}..."
briefcase build android

if [ -f "$APK_SOURCE" ]; then
    echo "Copying and renaming APK to $APK_DEST"
    cp "$APK_SOURCE" "$APK_DEST"
    echo "Success! Build created: $APK_DEST"
else
    echo "Error: APK not found at $APK_SOURCE"
    exit 1
fi
