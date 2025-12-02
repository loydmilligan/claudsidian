# Claudsidian Mobile

Android companion app for Claudsidian - share URLs from any app to capture them in your Obsidian vault.

## Features

- **Share Target**: Share URLs directly from any Android app (browser, Twitter, etc.)
- **Offline Queue**: URLs are queued locally when the server isn't available
- **Auto Discovery**: Finds your Claudsidian server automatically via mDNS
- **Auto Sync**: Queued URLs sync automatically when the server is found

## Requirements

- Android 5.0+ (API level 21)
- Flutter 3.10+ for building
- Claudsidian desktop server running with `--host 0.0.0.0 --advertise`

## Setup

### 1. Install Flutter

Follow the [Flutter installation guide](https://docs.flutter.dev/get-started/install).

### 2. Build the App

```bash
cd android
flutter pub get
flutter build apk --release
```

The APK will be at `build/app/outputs/flutter-apk/app-release.apk`.

### 3. Start Claudsidian Server

On your desktop, start the server with LAN access and mDNS advertisement:

```bash
claudsidian serve --host 0.0.0.0 --advertise
```

### 4. Use the App

1. Install the APK on your Android device
2. Open the app to see the connection status
3. Share a URL from any app - it will appear in the queue
4. The URL will sync automatically when the server is found

## Manual Server Configuration

If mDNS discovery doesn't work (some networks block multicast), you can manually enter the server address:

1. Open the app
2. Note your desktop's IP address
3. Use the "Add URL" button to test connectivity

## Project Structure

```
android/
├── lib/
│   ├── main.dart              # App entry point
│   ├── models/
│   │   └── queued_url.dart    # Queue item model
│   ├── services/
│   │   ├── share_handler.dart  # Handle shared URLs
│   │   ├── url_queue.dart      # Local queue with persistence
│   │   ├── server_discovery.dart # mDNS server discovery
│   │   └── sync_service.dart   # Queue sync to server
│   └── screens/
│       └── home_screen.dart    # Main UI
├── android/
│   └── app/src/main/
│       └── AndroidManifest.xml # Share intent filters
└── pubspec.yaml               # Dependencies
```

## Dependencies

- `receive_sharing_intent` - Handle Android share intents
- `nsd` - Network Service Discovery (mDNS)
- `http` - HTTP client for API calls
- `shared_preferences` - Local storage for queue persistence

## Troubleshooting

### Server not found

1. Ensure your phone and desktop are on the same WiFi network
2. Check that the server is running with `--advertise` flag
3. Some networks block mDNS - try entering the IP manually

### URLs not syncing

1. Check the server is running and accessible
2. Tap the sync button to force a sync attempt
3. Check the queue for error messages

### App not appearing in share menu

1. Restart the device after installation
2. Clear the default app associations in Android settings
