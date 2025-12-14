/// Settings screen for server configuration.
library;

import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/server_discovery.dart';

/// Settings screen for configuring server connection.
class SettingsScreen extends StatefulWidget {
  final ApiService apiService;
  final ServerDiscovery serverDiscovery;

  const SettingsScreen({
    super.key,
    required this.apiService,
    required this.serverDiscovery,
  });

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _urlController = TextEditingController();
  bool _isTesting = false;
  String? _testResult;
  bool _testSuccess = false;

  @override
  void initState() {
    super.initState();
    _urlController.text = widget.serverDiscovery.configuredUrl ?? '';
    widget.serverDiscovery.addListener(_onDiscoveryChanged);
    widget.apiService.addListener(_onApiChanged);
  }

  @override
  void dispose() {
    _urlController.dispose();
    widget.serverDiscovery.removeListener(_onDiscoveryChanged);
    widget.apiService.removeListener(_onApiChanged);
    super.dispose();
  }

  void _onDiscoveryChanged() {
    if (mounted) setState(() {});
  }

  void _onApiChanged() {
    if (mounted) setState(() {});
  }

  Future<void> _saveAndTest() async {
    final url = _urlController.text.trim();

    setState(() {
      _isTesting = true;
      _testResult = null;
    });

    try {
      if (url.isEmpty) {
        await widget.serverDiscovery.setServerUrl(null);
        setState(() {
          _testResult = 'URL cleared. Using auto-discovery.';
          _testSuccess = true;
        });
      } else {
        await widget.serverDiscovery.setServerUrl(url);
        final success = await widget.apiService.setServerUrl(url);

        setState(() {
          if (success) {
            _testResult = 'Connected successfully!';
            _testSuccess = true;
          } else {
            _testResult = widget.apiService.lastError ?? 'Connection failed';
            _testSuccess = false;
          }
        });
      }
    } catch (e) {
      setState(() {
        _testResult = e.toString();
        _testSuccess = false;
      });
    }

    setState(() => _isTesting = false);
  }

  @override
  Widget build(BuildContext context) {
    final isConnected = widget.apiService.isConnected;
    final discoveredServers = widget.serverDiscovery.servers;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Server Settings'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Connection status
          Card(
            color: isConnected
                ? Colors.green.withOpacity(0.1)
                : Colors.red.withOpacity(0.1),
            child: ListTile(
              leading: Icon(
                isConnected ? Icons.cloud_done : Icons.cloud_off,
                color: isConnected ? Colors.green : Colors.red,
              ),
              title: Text(isConnected ? 'Connected' : 'Not Connected'),
              subtitle: Text(
                isConnected
                    ? widget.apiService.baseUrl ?? ''
                    : widget.apiService.lastError ?? 'No server configured',
              ),
            ),
          ),
          const SizedBox(height: 24),

          // Server URL input
          Text(
            'Server URL',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _urlController,
            decoration: const InputDecoration(
              hintText: 'https://claudsidian.example.com',
              labelText: 'Server URL',
              helperText: 'Leave empty to use auto-discovery',
              border: OutlineInputBorder(),
            ),
            keyboardType: TextInputType.url,
          ),
          const SizedBox(height: 16),

          // Test result
          if (_testResult != null)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: _testSuccess
                    ? Colors.green.withOpacity(0.1)
                    : Colors.red.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: _testSuccess ? Colors.green : Colors.red,
                  width: 1,
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    _testSuccess ? Icons.check_circle : Icons.error,
                    color: _testSuccess ? Colors.green : Colors.red,
                  ),
                  const SizedBox(width: 12),
                  Expanded(child: Text(_testResult!)),
                ],
              ),
            ),
          const SizedBox(height: 16),

          // Save button
          FilledButton.icon(
            onPressed: _isTesting ? null : _saveAndTest,
            icon: _isTesting
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.save),
            label: Text(_isTesting ? 'Testing...' : 'Save & Test'),
          ),
          const SizedBox(height: 32),

          // Discovered servers
          Row(
            children: [
              Text(
                'Discovered Servers',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const Spacer(),
              if (widget.serverDiscovery.isDiscovering)
                const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              else
                IconButton(
                  icon: const Icon(Icons.refresh),
                  onPressed: () {
                    widget.serverDiscovery.stopDiscovery();
                    widget.serverDiscovery.startDiscovery();
                  },
                  tooltip: 'Scan network',
                ),
            ],
          ),
          const SizedBox(height: 8),

          if (discoveredServers.isEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  children: [
                    Icon(
                      Icons.wifi_find,
                      size: 48,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'No servers found on local network',
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Make sure claudsidian serve --advertise is running',
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                        fontSize: 12,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            )
          else
            ...discoveredServers.map((server) => Card(
                  child: ListTile(
                    leading: Icon(
                      server.isManualUrl ? Icons.link : Icons.wifi,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                    title: Text(server.name ?? server.host),
                    subtitle: Text(server.baseUrl),
                    trailing: IconButton(
                      icon: const Icon(Icons.arrow_forward),
                      onPressed: () {
                        _urlController.text = server.baseUrl;
                        _saveAndTest();
                      },
                    ),
                  ),
                )),
          const SizedBox(height: 24),

          // Help text
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(
                        Icons.help_outline,
                        size: 20,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'How to connect',
                        style: Theme.of(context).textTheme.titleSmall,
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    '1. On your computer, run:\n'
                    '   claudsidian serve --host 0.0.0.0 --advertise\n\n'
                    '2. Make sure your phone is on the same WiFi network\n\n'
                    '3. Either:\n'
                    '   \u2022 Wait for auto-discovery, or\n'
                    '   \u2022 Enter the server URL manually above',
                    style: TextStyle(fontSize: 13, height: 1.5),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
