/// Sync service for sending queued URLs to the server.
///
/// Monitors the server discovery and URL queue, sending pending URLs
/// when a server is available.
library;

import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/queued_url.dart';
import 'url_queue.dart';
import 'server_discovery.dart';

/// Sync status for the service.
enum SyncStatus {
  /// Not currently syncing
  idle,

  /// Currently syncing URLs
  syncing,

  /// No server available
  noServer,

  /// Error occurred during sync
  error,
}

/// Syncs queued URLs to the Claudsidian server.
///
/// Automatically sends pending URLs when a server is discovered.
/// Retries failed URLs with exponential backoff.
class SyncService extends ChangeNotifier {
  final UrlQueue _urlQueue;
  final ServerDiscovery _serverDiscovery;

  Timer? _syncTimer;
  bool _isSyncing = false;
  SyncStatus _status = SyncStatus.idle;
  String? _lastError;
  int _syncedCount = 0;
  int _failedCount = 0;

  /// Interval between sync attempts in seconds.
  static const int syncIntervalSeconds = 30;

  /// Maximum retry attempts before giving up.
  static const int maxRetryAttempts = 5;

  /// Create a new sync service.
  SyncService({
    required UrlQueue urlQueue,
    required ServerDiscovery serverDiscovery,
  })  : _urlQueue = urlQueue,
        _serverDiscovery = serverDiscovery;

  /// Current sync status.
  SyncStatus get status => _status;

  /// Last error message.
  String? get lastError => _lastError;

  /// Number of URLs synced in last batch.
  int get syncedCount => _syncedCount;

  /// Number of URLs that failed in last batch.
  int get failedCount => _failedCount;

  /// Whether sync is in progress.
  bool get isSyncing => _isSyncing;

  /// Start the sync service.
  void start() {
    // Listen for queue changes
    _urlQueue.addListener(_onQueueChanged);

    // Listen for server discovery
    _serverDiscovery.addListener(_onServerChanged);

    // Start periodic sync timer
    _syncTimer = Timer.periodic(
      const Duration(seconds: syncIntervalSeconds),
      (_) => _trySyncAll(),
    );

    // Initial sync attempt
    _trySyncAll();
  }

  /// Stop the sync service.
  void stop() {
    _syncTimer?.cancel();
    _syncTimer = null;
    _urlQueue.removeListener(_onQueueChanged);
    _serverDiscovery.removeListener(_onServerChanged);
  }

  /// Clean up resources.
  @override
  void dispose() {
    stop();
    super.dispose();
  }

  /// Handle queue changes.
  void _onQueueChanged() {
    // Try to sync when new items are added
    if (_urlQueue.pendingCount > 0 && !_isSyncing) {
      _trySyncAll();
    }
  }

  /// Handle server discovery changes.
  void _onServerChanged() {
    // Try to sync when a server becomes available
    if (_serverDiscovery.hasServers && !_isSyncing) {
      _trySyncAll();
    }
  }

  /// Attempt to sync all pending URLs.
  Future<void> _trySyncAll() async {
    if (_isSyncing) return;
    if (!_serverDiscovery.hasServers) {
      _updateStatus(SyncStatus.noServer);
      return;
    }
    if (_urlQueue.pendingCount == 0) {
      _updateStatus(SyncStatus.idle);
      return;
    }

    _isSyncing = true;
    _updateStatus(SyncStatus.syncing);
    _syncedCount = 0;
    _failedCount = 0;

    final server = _serverDiscovery.primaryServer!;
    final pendingItems = _urlQueue.pendingItems;

    for (final item in pendingItems) {
      // Skip items that have exceeded retry attempts
      if (item.attempts >= maxRetryAttempts) {
        continue;
      }

      final success = await _syncUrl(item, server);
      if (success) {
        _syncedCount++;
      } else {
        _failedCount++;
      }
    }

    _isSyncing = false;

    if (_failedCount > 0) {
      _updateStatus(SyncStatus.error);
    } else {
      _updateStatus(SyncStatus.idle);
    }
  }

  /// Sync a single URL to the server.
  Future<bool> _syncUrl(QueuedUrl item, DiscoveredServer server) async {
    await _urlQueue.updateStatus(item.id, QueuedUrlStatus.sending);

    try {
      final response = await http.post(
        Uri.parse(server.captureUrl),
        headers: {
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'url': item.url,
          'source': 'mobile',
        }),
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode >= 200 && response.statusCode < 300) {
        await _urlQueue.updateStatus(item.id, QueuedUrlStatus.sent);
        print('Synced URL: ${item.url}');
        return true;
      } else {
        final error = 'Server returned ${response.statusCode}';
        await _urlQueue.updateStatus(
          item.id,
          QueuedUrlStatus.failed,
          error: error,
        );
        print('Failed to sync URL: ${item.url} - $error');
        return false;
      }
    } catch (e) {
      final error = e.toString();
      await _urlQueue.updateStatus(
        item.id,
        QueuedUrlStatus.failed,
        error: error,
      );
      print('Error syncing URL: ${item.url} - $error');
      return false;
    }
  }

  /// Force an immediate sync attempt.
  Future<void> syncNow() async {
    await _trySyncAll();
  }

  /// Update status and notify listeners.
  void _updateStatus(SyncStatus status, {String? error}) {
    _status = status;
    _lastError = error;
    notifyListeners();
  }
}
