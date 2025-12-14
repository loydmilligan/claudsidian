/// API service for communicating with Claudsidian server.
library;

import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/capture_result.dart';
import '../models/capture_options.dart';
import '../models/ai_model.dart';
import '../models/research_subject.dart';

/// Service for API calls to the Claudsidian server.
class ApiService extends ChangeNotifier {
  String? _baseUrl;
  bool _isConnected = false;
  String? _lastError;

  // Cached data
  ModelsResponse? _modelsCache;
  SubjectsResponse? _subjectsCache;
  DateTime? _modelsCacheTime;
  DateTime? _subjectsCacheTime;

  static const _cacheTimeout = Duration(minutes: 5);
  static const _httpTimeout = Duration(seconds: 30);

  /// Current base URL.
  String? get baseUrl => _baseUrl;

  /// Whether connected to server.
  bool get isConnected => _isConnected;

  /// Last error message.
  String? get lastError => _lastError;

  /// Set the server URL and test connection.
  Future<bool> setServerUrl(String? url) async {
    if (url == null || url.isEmpty) {
      _baseUrl = null;
      _isConnected = false;
      notifyListeners();
      return false;
    }

    // Normalize URL
    String normalizedUrl = url.trim();
    if (!normalizedUrl.startsWith('http://') &&
        !normalizedUrl.startsWith('https://')) {
      normalizedUrl = 'https://$normalizedUrl';
    }
    if (normalizedUrl.endsWith('/')) {
      normalizedUrl = normalizedUrl.substring(0, normalizedUrl.length - 1);
    }

    _baseUrl = normalizedUrl;
    return await testConnection();
  }

  /// Test connection to server.
  Future<bool> testConnection() async {
    if (_baseUrl == null) return false;

    try {
      final response = await http
          .get(Uri.parse('$_baseUrl/health'))
          .timeout(_httpTimeout);

      _isConnected = response.statusCode == 200;
      _lastError = _isConnected ? null : 'Server returned ${response.statusCode}';
    } catch (e) {
      _isConnected = false;
      _lastError = e.toString().replaceAll('Exception: ', '');
    }

    notifyListeners();
    return _isConnected;
  }

  /// Capture a URL.
  Future<CaptureResult> capture(String url, {CaptureOptions? options}) async {
    if (_baseUrl == null) {
      throw Exception('Server not configured');
    }

    options ??= CaptureOptions.defaults();

    final body = options.toJson();
    body['url'] = url;

    try {
      final response = await http
          .post(
            Uri.parse('$_baseUrl/capture'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(body),
          )
          .timeout(_httpTimeout);

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body);
        _isConnected = true;
        notifyListeners();
        return CaptureResult.fromJson(data, url);
      } else if (response.statusCode == 409) {
        final data = jsonDecode(response.body);
        throw DuplicateException(data['existing_note'] ?? 'Already captured');
      } else {
        final data = jsonDecode(response.body);
        throw Exception(data['message'] ?? 'Capture failed');
      }
    } catch (e) {
      if (e is DuplicateException) rethrow;
      _lastError = e.toString();
      notifyListeners();
      rethrow;
    }
  }

  /// Get available AI models.
  Future<ModelsResponse> getModels({bool forceRefresh = false}) async {
    if (_baseUrl == null) {
      throw Exception('Server not configured');
    }

    // Check cache
    if (!forceRefresh &&
        _modelsCache != null &&
        _modelsCacheTime != null &&
        DateTime.now().difference(_modelsCacheTime!) < _cacheTimeout) {
      return _modelsCache!;
    }

    try {
      final response = await http
          .get(Uri.parse('$_baseUrl/models'))
          .timeout(_httpTimeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _modelsCache = ModelsResponse.fromJson(data);
        _modelsCacheTime = DateTime.now();
        return _modelsCache!;
      } else {
        throw Exception('Failed to load models');
      }
    } catch (e) {
      _lastError = e.toString();
      rethrow;
    }
  }

  /// Get research subjects.
  Future<SubjectsResponse> getSubjects({bool forceRefresh = false}) async {
    if (_baseUrl == null) {
      throw Exception('Server not configured');
    }

    // Check cache
    if (!forceRefresh &&
        _subjectsCache != null &&
        _subjectsCacheTime != null &&
        DateTime.now().difference(_subjectsCacheTime!) < _cacheTimeout) {
      return _subjectsCache!;
    }

    try {
      final response = await http
          .get(Uri.parse('$_baseUrl/subjects'))
          .timeout(_httpTimeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _subjectsCache = SubjectsResponse.fromJson(data);
        _subjectsCacheTime = DateTime.now();
        return _subjectsCache!;
      } else {
        throw Exception('Failed to load subjects');
      }
    } catch (e) {
      _lastError = e.toString();
      rethrow;
    }
  }

  /// Create a new research subject.
  Future<ResearchSubject> createSubject(String name) async {
    if (_baseUrl == null) {
      throw Exception('Server not configured');
    }

    try {
      final response = await http
          .post(
            Uri.parse('$_baseUrl/subjects'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'name': name}),
          )
          .timeout(_httpTimeout);

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body);
        // Invalidate cache
        _subjectsCache = null;
        return ResearchSubject(name: data['name'] ?? name);
      } else {
        final data = jsonDecode(response.body);
        throw Exception(data['message'] ?? 'Failed to create subject');
      }
    } catch (e) {
      _lastError = e.toString();
      rethrow;
    }
  }

  /// Get server stats.
  Future<Map<String, dynamic>> getStats() async {
    if (_baseUrl == null) {
      throw Exception('Server not configured');
    }

    try {
      final response = await http
          .get(Uri.parse('$_baseUrl/stats'))
          .timeout(_httpTimeout);

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to load stats');
      }
    } catch (e) {
      _lastError = e.toString();
      rethrow;
    }
  }

  /// Clear caches.
  void clearCache() {
    _modelsCache = null;
    _subjectsCache = null;
    _modelsCacheTime = null;
    _subjectsCacheTime = null;
  }
}

/// Exception for duplicate captures.
class DuplicateException implements Exception {
  final String existingNote;

  DuplicateException(this.existingNote);

  @override
  String toString() => 'Already captured: $existingNote';
}
