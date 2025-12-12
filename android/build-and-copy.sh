#!/bin/bash
# Build Claudsidian Android app and copy to Downloads

export PATH="$HOME/android-dev/flutter/bin:$PATH"

cd /home/mmariani/Projects/claudsidian/android

echo "Building APK..."
flutter build apk --debug

if [ $? -eq 0 ]; then
    echo "Copying to Downloads..."
    cp build/app/outputs/flutter-apk/app-debug.apk /mnt/c/Users/mmariani/Downloads/app-debug.apk
    echo ""
    echo "Done! Now run in PowerShell:"
    echo ".\adb install -r C:\Users\mmariani\Downloads\app-debug.apk"
else
    echo "Build failed!"
    exit 1
fi
