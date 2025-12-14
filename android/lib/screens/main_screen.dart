/// Main screen with tabs for Queue, History, and Stats.
library;

import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/capture_history.dart';
import '../services/server_discovery.dart';
import '../theme/app_theme.dart';
import 'queue_tab.dart';
import 'history_tab.dart';
import 'stats_tab.dart';
import 'settings_screen.dart';

/// Main screen with bottom navigation.
class MainScreen extends StatefulWidget {
  final ApiService apiService;
  final CaptureHistoryService captureHistory;
  final ServerDiscovery serverDiscovery;
  final void Function(String url) onShareUrl;

  const MainScreen({
    super.key,
    required this.apiService,
    required this.captureHistory,
    required this.serverDiscovery,
    required this.onShareUrl,
  });

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _currentIndex = 0;
  final _urlController = TextEditingController();

  @override
  void initState() {
    super.initState();
    widget.apiService.addListener(_onStateChanged);
    widget.captureHistory.addListener(_onStateChanged);
    widget.serverDiscovery.addListener(_onStateChanged);
  }

  @override
  void dispose() {
    widget.apiService.removeListener(_onStateChanged);
    widget.captureHistory.removeListener(_onStateChanged);
    widget.serverDiscovery.removeListener(_onStateChanged);
    _urlController.dispose();
    super.dispose();
  }

  void _onStateChanged() {
    if (mounted) setState(() {});
  }

  Future<void> _refresh() async {
    await widget.apiService.testConnection();
  }

  void _showCaptureDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Capture URL'),
        content: TextField(
          controller: _urlController,
          decoration: const InputDecoration(
            hintText: 'https://...',
            labelText: 'URL',
          ),
          autofocus: true,
          keyboardType: TextInputType.url,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              final url = _urlController.text.trim();
              if (url.isNotEmpty) {
                Navigator.pop(context);
                widget.onShareUrl(url);
                _urlController.clear();
              }
            },
            child: const Text('Capture'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isConnected = widget.apiService.isConnected;
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Claudsidian'),
        actions: [
          // Connection status indicator
          IconButton(
            icon: Icon(
              isConnected ? Icons.cloud_done : Icons.cloud_off,
              color: isConnected ? Colors.green : colorScheme.error,
            ),
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (context) => SettingsScreen(
                  apiService: widget.apiService,
                  serverDiscovery: widget.serverDiscovery,
                ),
              ),
            ),
            tooltip: isConnected ? 'Connected' : 'Not connected',
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: IndexedStack(
          index: _currentIndex,
          children: [
            QueueTab(
              apiService: widget.apiService,
              captureHistory: widget.captureHistory,
            ),
            HistoryTab(
              captureHistory: widget.captureHistory,
            ),
            StatsTab(
              apiService: widget.apiService,
              captureHistory: widget.captureHistory,
            ),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) {
          setState(() => _currentIndex = index);
        },
        destinations: [
          NavigationDestination(
            icon: const Icon(Icons.list_alt_outlined),
            selectedIcon: const Icon(Icons.list_alt),
            label: 'Queue',
          ),
          NavigationDestination(
            icon: const Icon(Icons.history_outlined),
            selectedIcon: const Icon(Icons.history),
            label: 'History',
          ),
          NavigationDestination(
            icon: const Icon(Icons.bar_chart_outlined),
            selectedIcon: const Icon(Icons.bar_chart),
            label: 'Stats',
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showCaptureDialog,
        icon: const Icon(Icons.add),
        label: const Text('Capture'),
      ),
    );
  }
}
