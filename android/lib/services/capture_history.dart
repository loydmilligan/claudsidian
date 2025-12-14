/// Service for tracking capture history.
library;

import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/capture_result.dart';

/// Service for managing capture history.
class CaptureHistoryService extends ChangeNotifier {
  static const String _prefsKey = 'capture_history';
  static const int _maxHistoryItems = 50;

  List<CaptureResult> _history = [];
  bool _initialized = false;

  /// Recent capture history (newest first).
  List<CaptureResult> get history => List.unmodifiable(_history);

  /// Whether the service is initialized.
  bool get isInitialized => _initialized;

  /// Most recent capture.
  CaptureResult? get lastCapture => _history.isNotEmpty ? _history.first : null;

  /// Count of captures.
  int get count => _history.length;

  /// Load history from storage.
  Future<void> load() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final jsonString = prefs.getString(_prefsKey);

      if (jsonString != null) {
        final jsonList = jsonDecode(jsonString) as List;
        _history = jsonList
            .map((item) =>
                CaptureResult.fromStoredJson(item as Map<String, dynamic>))
            .toList();
      }
    } catch (e) {
      print('Failed to load capture history: $e');
      _history = [];
    }

    _initialized = true;
    notifyListeners();
  }

  /// Add a capture to history.
  Future<void> addCapture(CaptureResult capture) async {
    // Remove if already exists (by URL)
    _history.removeWhere((c) => c.url == capture.url);

    // Add to front
    _history.insert(0, capture);

    // Trim to max size
    if (_history.length > _maxHistoryItems) {
      _history = _history.sublist(0, _maxHistoryItems);
    }

    await _save();
    notifyListeners();
  }

  /// Remove a capture from history.
  Future<void> removeCapture(String url) async {
    _history.removeWhere((c) => c.url == url);
    await _save();
    notifyListeners();
  }

  /// Clear all history.
  Future<void> clear() async {
    _history = [];
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_prefsKey);
    notifyListeners();
  }

  /// Get captures from today.
  List<CaptureResult> get todaysCaptures {
    final now = DateTime.now();
    final startOfDay = DateTime(now.year, now.month, now.day);
    return _history.where((c) => c.capturedAt.isAfter(startOfDay)).toList();
  }

  /// Get captures from this week.
  List<CaptureResult> get thisWeeksCaptures {
    final now = DateTime.now();
    final startOfWeek = now.subtract(Duration(days: now.weekday - 1));
    final startOfDay =
        DateTime(startOfWeek.year, startOfWeek.month, startOfWeek.day);
    return _history.where((c) => c.capturedAt.isAfter(startOfDay)).toList();
  }

  /// Get captures by content type.
  Map<ContentType, List<CaptureResult>> get capturesByType {
    final result = <ContentType, List<CaptureResult>>{};
    for (final capture in _history) {
      result.putIfAbsent(capture.contentType, () => []).add(capture);
    }
    return result;
  }

  /// Save history to storage.
  Future<void> _save() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final jsonList = _history.map((c) => c.toJson()).toList();
      await prefs.setString(_prefsKey, jsonEncode(jsonList));
    } catch (e) {
      print('Failed to save capture history: $e');
    }
  }
}
