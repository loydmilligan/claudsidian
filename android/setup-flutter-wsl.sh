#!/bin/bash
# Flutter + Android SDK setup script for WSL2
# Run this script with: bash setup-flutter-wsl.sh

set -e

INSTALL_DIR="$HOME/android-dev"
FLUTTER_VERSION="3.24.3"

echo "=== Claudsidian Android Build Environment Setup ==="
echo "Install directory: $INSTALL_DIR"
echo ""

# Step 1: Install Java (requires sudo)
echo "=== Step 1: Installing Java 17 ==="
sudo apt-get update
sudo apt-get install -y openjdk-17-jdk unzip wget curl git clang cmake ninja-build pkg-config libgtk-3-dev

# Verify Java
java -version
echo "Java installed successfully!"
echo ""

# Step 2: Download and install Flutter SDK
echo "=== Step 2: Installing Flutter SDK ==="
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

if [ ! -d "flutter" ]; then
    echo "Downloading Flutter $FLUTTER_VERSION..."
    wget -q --show-progress "https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_${FLUTTER_VERSION}-stable.tar.xz"
    echo "Extracting Flutter..."
    tar xf "flutter_linux_${FLUTTER_VERSION}-stable.tar.xz"
    rm "flutter_linux_${FLUTTER_VERSION}-stable.tar.xz"
    echo "Flutter installed!"
else
    echo "Flutter already installed, skipping download"
fi

# Step 3: Download Android command-line tools
echo "=== Step 3: Installing Android SDK ==="
mkdir -p "$INSTALL_DIR/android-sdk/cmdline-tools"
cd "$INSTALL_DIR/android-sdk/cmdline-tools"

if [ ! -d "latest" ]; then
    echo "Downloading Android command-line tools..."
    wget -q --show-progress "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
    unzip -q commandlinetools-linux-11076708_latest.zip
    mv cmdline-tools latest
    rm commandlinetools-linux-11076708_latest.zip
    echo "Android cmdline-tools installed!"
else
    echo "Android cmdline-tools already installed, skipping download"
fi

# Step 4: Set up environment variables
echo "=== Step 4: Configuring environment variables ==="

# Detect shell config file (zsh or bash)
if [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
    echo "Detected zsh, using ~/.zshrc"
else
    SHELL_RC="$HOME/.bashrc"
    echo "Using ~/.bashrc"
fi

# Check if already configured
if ! grep -q "ANDROID_SDK_ROOT" "$SHELL_RC"; then
    cat >> "$SHELL_RC" << 'ENVEOF'

# Flutter and Android SDK (added by Claudsidian setup)
export ANDROID_SDK_ROOT="$HOME/android-dev/android-sdk"
export ANDROID_HOME="$ANDROID_SDK_ROOT"
export PATH="$HOME/android-dev/flutter/bin:$PATH"
export PATH="$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$PATH"
export PATH="$ANDROID_SDK_ROOT/platform-tools:$PATH"
export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
ENVEOF
    echo "Environment variables added to $SHELL_RC"
else
    echo "Environment variables already configured"
fi

# Source for current session
export ANDROID_SDK_ROOT="$HOME/android-dev/android-sdk"
export ANDROID_HOME="$ANDROID_SDK_ROOT"
export PATH="$HOME/android-dev/flutter/bin:$PATH"
export PATH="$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$PATH"
export PATH="$ANDROID_SDK_ROOT/platform-tools:$PATH"
export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"

# Step 5: Accept Android licenses and install SDK components
echo "=== Step 5: Installing Android SDK components ==="
yes | sdkmanager --licenses 2>/dev/null || true
sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"
echo "Android SDK components installed!"

# Step 6: Configure Flutter
echo "=== Step 6: Configuring Flutter ==="
flutter config --android-sdk "$ANDROID_SDK_ROOT"
flutter config --no-analytics

# Step 7: Run Flutter doctor
echo "=== Step 7: Running Flutter Doctor ==="
flutter doctor -v

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Please run: source $SHELL_RC"
echo "Then cd to /home/mmariani/Projects/claudsidian/android"
echo "And run: flutter pub get && flutter build apk --release"
echo ""
echo "The APK will be at: build/app/outputs/flutter-apk/app-release.apk"
