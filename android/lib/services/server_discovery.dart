/// Server discovery service using mDNS/NSD.
///
/// Discovers Claudsidian servers on the local network using
/// Network Service Discovery (NSD/mDNS).
library;

import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:nsd/nsd.dart' as nsd;
import 'package:shared_preferences/shared_preferences.dart';

/// Information about a discovered Claudsidian server.
class DiscoveredServer {
  /// Server hostname or IP address
  final String host;

  /// Server port number
  final int port;

  /// Server name from mDNS advertisement
  final String? name;

  /// API version if available
  final String? version;

  /// Whether this is a manually configured URL (not discovered)
  final bool isManualUrl;

  /// The original URL if configured via URL
  final String? configuredUrl;

  /// Create a discovered server entry.
  const DiscoveredServer({
    required this.host,
    required this.port,
    this.name,
    this.version,
    this.isManualUrl = false,
    this.configuredUrl,
  });

  /// Create from a full URL string.
  ///
  /// Parses URLs like:
  /// - https://claudsidian.example.com
  /// - http://192.168.1.100:8765
  /// - claudsidian.example.com (assumes https, port 443)
  factory DiscoveredServer.fromUrl(String url) {
    // Normalize the URL
    String normalizedUrl = url.trim();

    // Add protocol if missing
    if (!normalizedUrl.startsWith('http://') && !normalizedUrl.startsWith('https://')) {
      normalizedUrl = 'https://$normalizedUrl';
    }

    final uri = Uri.parse(normalizedUrl);

    // Determine port
    int port;
    if (uri.hasPort) {
      port = uri.port;
    } else {
      port = uri.scheme == 'https' ? 443 : 80;
    }

    return DiscoveredServer(
      host: uri.host,
      port: port,
      name: 'Custom: ${uri.host}',
      isManualUrl: true,
      configuredUrl: normalizedUrl,
    );
  }

  /// Full base URL for API requests.
  String get baseUrl {
    if (configuredUrl != null) {
      // Use the configured URL, removing trailing slash
      return configuredUrl!.endsWith('/')
          ? configuredUrl!.substring(0, configuredUrl!.length - 1)
          : configuredUrl!;
    }
    return 'http://$host:$port';
  }

  /// Capture endpoint URL.
  String get captureUrl => '$baseUrl/capture';

  @override
  String toString() => 'DiscoveredServer($name at $host:$port)';
}

/// Discovers Claudsidian servers on the local network.
///
/// Uses mDNS to find servers advertising the `_claudsidian._tcp` service.
/// Also supports manually configured server URLs.
class ServerDiscovery extends ChangeNotifier {
  static const String serviceType = '_claudsidian._tcp';
  static const String _prefsKeyServerUrl = 'claudsidian_server_url';

  nsd.Discovery? _discovery;
  final List<DiscoveredServer> _servers = [];
  bool _isDiscovering = false;
  String? _error;
  String? _configuredUrl;

  /// List of discovered servers.
  List<DiscoveredServer> get servers => List.unmodifiable(_servers);

  /// The first discovered server, or null if none found.
  DiscoveredServer? get primaryServer => _servers.isNotEmpty ? _servers.first : null;

  /// Whether discovery is currently running.
  bool get isDiscovering => _isDiscovering;

  /// Whether any servers have been discovered.
  bool get hasServers => _servers.isNotEmpty;

  /// Last error message, if any.
  String? get error => _error;

  /// The currently configured server URL (if any).
  String? get configuredUrl => _configuredUrl;

  /// Whether a custom URL is configured.
  bool get hasConfiguredUrl => _configuredUrl != null && _configuredUrl!.isNotEmpty;

  /// Load saved server URL from preferences.
  Future<void> loadSavedUrl() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedUrl = prefs.getString(_prefsKeyServerUrl);
      if (savedUrl != null && savedUrl.isNotEmpty) {
        _configuredUrl = savedUrl;
        _addServerFromUrl(savedUrl);
      }
    } catch (e) {
      print('Failed to load saved server URL: $e');
    }
  }

  /// Set a custom server URL.
  ///
  /// Pass null or empty string to clear the custom URL.
  Future<void> setServerUrl(String? url) async {
    // Remove existing manual URL servers
    _servers.removeWhere((s) => s.isManualUrl);

    if (url != null && url.trim().isNotEmpty) {
      _configuredUrl = url.trim();
      _addServerFromUrl(_configuredUrl!);

      // Save to preferences
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_prefsKeyServerUrl, _configuredUrl!);
    } else {
      _configuredUrl = null;

      // Clear from preferences
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_prefsKeyServerUrl);
    }

    notifyListeners();
  }

  /// Add a server from a URL string.
  void _addServerFromUrl(String url) {
    try {
      final server = DiscoveredServer.fromUrl(url);
      // Insert at the front so it takes priority
      _servers.insert(0, server);
      print('Added server from URL: $server');
    } catch (e) {
      print('Failed to parse server URL: $e');
      _error = 'Invalid URL: $url';
    }
  }

  /// Start discovering servers on the local network.
  Future<void> startDiscovery() async {
    if (_isDiscovering) return;

    _isDiscovering = true;
    _error = null;
    notifyListeners();

    try {
      _discovery = await nsd.startDiscovery(serviceType, ipLookupType: nsd.IpLookupType.v4);

      _discovery!.addServiceListener((service, status) {
        switch (status) {
          case nsd.ServiceStatus.found:
            _addServer(service);
            break;
          case nsd.ServiceStatus.lost:
            _removeServer(service);
            break;
        }
      });
    } catch (e) {
      _error = 'Failed to start discovery: $e';
      _isDiscovering = false;
      notifyListeners();
    }
  }

  /// Stop discovering servers.
  Future<void> stopDiscovery() async {
    if (_discovery != null) {
      await nsd.stopDiscovery(_discovery!);
      _discovery = null;
    }
    _isDiscovering = false;
    notifyListeners();
  }

  /// Add a discovered server to the list.
  void _addServer(nsd.Service service) {
    // Extract host from addresses
    String? host;
    if (service.addresses != null && service.addresses!.isNotEmpty) {
      // Prefer IPv4 addresses (those without colons)
      final ipv4 = service.addresses!.where((a) => !a.address.contains(':')).toList();
      if (ipv4.isNotEmpty) {
        host = ipv4.first.address;
      } else {
        host = service.addresses!.first.address;
      }
    }

    if (host == null || service.port == null) {
      print('Discovered service without host/port: ${service.name}');
      return;
    }

    // Check for duplicates
    final exists = _servers.any((s) => s.host == host && s.port == service.port);
    if (exists) return;

    // Extract version from TXT records if available
    String? version;
    if (service.txt != null && service.txt!.containsKey('version')) {
      final versionBytes = service.txt!['version'];
      if (versionBytes != null) {
        version = String.fromCharCodes(versionBytes);
      }
    }

    final server = DiscoveredServer(
      host: host,
      port: service.port!,
      name: service.name,
      version: version,
    );

    _servers.add(server);
    print('Discovered server: $server');
    notifyListeners();
  }

  /// Remove a server from the list when it goes offline.
  void _removeServer(nsd.Service service) {
    _servers.removeWhere((s) => s.name == service.name);
    print('Server went offline: ${service.name}');
    notifyListeners();
  }

  /// Manually add a server by IP/port (for direct connection).
  void addManualServer(String host, int port) {
    final exists = _servers.any((s) => s.host == host && s.port == port);
    if (exists) return;

    _servers.insert(
      0,
      DiscoveredServer(
        host: host,
        port: port,
        name: 'Manual: $host:$port',
      ),
    );
    notifyListeners();
  }

  /// Clear all discovered servers.
  void clearServers() {
    _servers.clear();
    notifyListeners();
  }

  /// Clean up resources.
  @override
  void dispose() {
    stopDiscovery();
    super.dispose();
  }
}
