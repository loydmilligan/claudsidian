/// Claudsidian Mobile - Android share target for URL capture
library;

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:receive_sharing_intent/receive_sharing_intent.dart';

import 'theme/app_theme.dart';
import 'services/api_service.dart';
import 'services/capture_history.dart';
import 'services/server_discovery.dart';
import 'models/capture_result.dart';
import 'models/capture_options.dart';
import 'screens/main_screen.dart';
import 'screens/capture_sheet.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SharedPreferences.getInstance();
  runApp(const ClaudsidianApp());
}

/// Main application widget.
class ClaudsidianApp extends StatefulWidget {
  const ClaudsidianApp({super.key});

  @override
  State<ClaudsidianApp> createState() => _ClaudsidianAppState();
}

class _ClaudsidianAppState extends State<ClaudsidianApp> {
  // Services
  final _apiService = ApiService();
  final _captureHistory = CaptureHistoryService();
  final _serverDiscovery = ServerDiscovery();

  // Share handling
  StreamSubscription? _intentSubscription;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    // Load saved data
    await _captureHistory.load();
    await _serverDiscovery.loadSavedUrl();

    // Set up API service with saved URL
    if (_serverDiscovery.hasConfiguredUrl) {
      await _apiService.setServerUrl(_serverDiscovery.configuredUrl);
    } else if (_serverDiscovery.hasServers) {
      await _apiService.setServerUrl(_serverDiscovery.primaryServer!.baseUrl);
    }

    // Start server discovery
    _serverDiscovery.startDiscovery();

    // Listen for server discovery updates
    _serverDiscovery.addListener(_onServerDiscoveryUpdate);

    // Set up share listener
    _setupShareListener();
  }

  void _onServerDiscoveryUpdate() {
    // Auto-connect to discovered server if not configured
    if (!_serverDiscovery.hasConfiguredUrl &&
        _serverDiscovery.hasServers &&
        !_apiService.isConnected) {
      _apiService.setServerUrl(_serverDiscovery.primaryServer!.baseUrl);
    }
  }

  void _setupShareListener() {
    // Handle shares when app is running
    _intentSubscription = ReceiveSharingIntent.instance
        .getMediaStream()
        .listen(_handleSharedMedia, onError: (err) {
      print('Share stream error: $err');
    });

    // Handle initial share (app was launched via share)
    ReceiveSharingIntent.instance.getInitialMedia().then((files) {
      if (files.isNotEmpty) {
        _handleSharedMedia(files);
        ReceiveSharingIntent.instance.reset();
      }
    });
  }

  void _handleSharedMedia(List<SharedMediaFile> files) {
    for (final file in files) {
      String? text = file.path;
      if (text.isEmpty && file.message != null) {
        text = file.message;
      }
      if (text == null || text.isEmpty) continue;

      // Extract URL from shared text
      final urlMatch = RegExp(r'https?://[^\s]+').firstMatch(text);
      if (urlMatch != null) {
        final url = urlMatch.group(0)!;
        _showCaptureSheet(url);
      }
    }
  }

  void _showCaptureSheet(String url) {
    // Use global navigator key to show bottom sheet
    final context = _navigatorKey.currentContext;
    if (context == null) return;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (context) => CaptureSheet(
        url: url,
        apiService: _apiService,
        captureHistory: _captureHistory,
        onCaptured: (result) {
          _showCaptureToast(context, result);
        },
      ),
    );
  }

  void _showCaptureToast(BuildContext context, CaptureResult result) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            ContentTypeBadge(
              type: result.contentType.name,
              showEmoji: true,
              fontSize: 12,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                result.title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        action: SnackBarAction(
          label: 'View',
          onPressed: () {
            // TODO: Open note in Obsidian
          },
        ),
        duration: const Duration(seconds: 4),
      ),
    );
  }

  @override
  void dispose() {
    _intentSubscription?.cancel();
    _serverDiscovery.removeListener(_onServerDiscoveryUpdate);
    _serverDiscovery.dispose();
    super.dispose();
  }

  final _navigatorKey = GlobalKey<NavigatorState>();

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: _navigatorKey,
      title: 'Claudsidian',
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.system,
      home: MainScreen(
        apiService: _apiService,
        captureHistory: _captureHistory,
        serverDiscovery: _serverDiscovery,
        onShareUrl: _showCaptureSheet,
      ),
    );
  }
}
