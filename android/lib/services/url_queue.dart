/// Local URL queue service with persistence.
///
/// Stores URLs locally when the server is unavailable and syncs them
/// when the server is discovered.
library;

import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/queued_url.dart';

/// Manages a local queue of URLs to be sent to the Claudsidian server.
///
/// URLs are persisted to local storage so they survive app restarts.
/// The queue notifies listeners when items are added or updated.
class UrlQueue extends ChangeNotifier {
  static const String _storageKey = 'claudsidian_url_queue';

  late SharedPreferences _prefs;
  final List<QueuedUrl> _queue = [];
  bool _initialized = false;

  /// Whether the queue has been initialized.
  bool get isInitialized => _initialized;

  /// All queued URLs.
  List<QueuedUrl> get items => List.unmodifiable(_queue);

  /// URLs waiting to be sent (pending or failed).
  List<QueuedUrl> get pendingItems => _queue
      .where((item) =>
          item.status == QueuedUrlStatus.pending ||
          item.status == QueuedUrlStatus.failed)
      .toList();

  /// Number of pending items.
  int get pendingCount => pendingItems.length;

  /// Initialize the queue and load persisted URLs.
  Future<void> initialize() async {
    if (_initialized) return;

    _prefs = await SharedPreferences.getInstance();
    await _loadFromStorage();
    _initialized = true;
    notifyListeners();
  }

  /// Alias for initialize() for consistency.
  Future<void> load() => initialize();

  /// Mark item as failed with error message.
  Future<void> markFailed(String id, String error) async {
    await updateStatus(id, QueuedUrlStatus.failed, error: error);
  }

  /// Add a URL to the queue.
  Future<void> addUrl(String url) async {
    // Check for duplicates
    final exists = _queue.any((item) => item.url == url);
    if (exists) {
      print('URL already in queue: $url');
      return;
    }

    final queuedUrl = QueuedUrl.create(url);
    _queue.add(queuedUrl);
    await _saveToStorage();
    notifyListeners();
  }

  /// Get a URL by ID.
  QueuedUrl? getById(String id) {
    try {
      return _queue.firstWhere((item) => item.id == id);
    } catch (_) {
      return null;
    }
  }

  /// Update a queued URL's status.
  Future<void> updateStatus(
    String id,
    QueuedUrlStatus status, {
    String? error,
  }) async {
    final item = getById(id);
    if (item == null) return;

    switch (status) {
      case QueuedUrlStatus.sending:
        item.markSending();
        break;
      case QueuedUrlStatus.sent:
        item.markSent();
        break;
      case QueuedUrlStatus.failed:
        item.markFailed(error ?? 'Unknown error');
        break;
      case QueuedUrlStatus.pending:
        item.resetToPending();
        break;
    }

    await _saveToStorage();
    notifyListeners();
  }

  /// Remove a URL from the queue.
  Future<void> remove(String id) async {
    _queue.removeWhere((item) => item.id == id);
    await _saveToStorage();
    notifyListeners();
  }

  /// Remove all sent items from the queue.
  Future<void> clearSent() async {
    _queue.removeWhere((item) => item.status == QueuedUrlStatus.sent);
    await _saveToStorage();
    notifyListeners();
  }

  /// Clear all items from the queue.
  Future<void> clearAll() async {
    _queue.clear();
    await _saveToStorage();
    notifyListeners();
  }

  /// Retry all failed items.
  Future<void> retryFailed() async {
    for (final item in _queue) {
      if (item.status == QueuedUrlStatus.failed) {
        item.resetToPending();
      }
    }
    await _saveToStorage();
    notifyListeners();
  }

  /// Load queue from local storage.
  Future<void> _loadFromStorage() async {
    final json = _prefs.getString(_storageKey);
    if (json == null || json.isEmpty) return;

    try {
      final List<dynamic> items = jsonDecode(json);
      _queue.clear();
      for (final item in items) {
        _queue.add(QueuedUrl.fromJson(item as Map<String, dynamic>));
      }
    } catch (e) {
      print('Error loading queue from storage: $e');
    }
  }

  /// Save queue to local storage.
  Future<void> _saveToStorage() async {
    try {
      final json = jsonEncode(_queue.map((item) => item.toJson()).toList());
      await _prefs.setString(_storageKey, json);
    } catch (e) {
      print('Error saving queue to storage: $e');
    }
  }
}
