/// Home screen showing queue status and server connection.
library;

import 'package:flutter/material.dart';
import '../services/url_queue.dart';
import '../services/server_discovery.dart';
import '../services/sync_service.dart';
import '../models/queued_url.dart';

/// Main screen of the Claudsidian mobile app.
///
/// Shows:
/// - Server connection status
/// - Queue of pending URLs
/// - Sync status and controls
class HomeScreen extends StatefulWidget {
  final UrlQueue urlQueue;
  final ServerDiscovery serverDiscovery;
  final SyncService syncService;

  const HomeScreen({
    super.key,
    required this.urlQueue,
    required this.serverDiscovery,
    required this.syncService,
  });

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    widget.urlQueue.addListener(_onStateChanged);
    widget.serverDiscovery.addListener(_onStateChanged);
    widget.syncService.addListener(_onStateChanged);
  }

  @override
  void dispose() {
    widget.urlQueue.removeListener(_onStateChanged);
    widget.serverDiscovery.removeListener(_onStateChanged);
    widget.syncService.removeListener(_onStateChanged);
    super.dispose();
  }

  void _onStateChanged() {
    if (mounted) {
      setState(() {});
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Claudsidian'),
        actions: [
          IconButton(
            icon: const Icon(Icons.sync),
            onPressed: widget.syncService.isSyncing
                ? null
                : () => widget.syncService.syncNow(),
            tooltip: 'Sync now',
          ),
        ],
      ),
      body: Column(
        children: [
          _buildServerStatus(),
          const Divider(),
          _buildSyncStatus(),
          const Divider(),
          Expanded(child: _buildQueueList()),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showAddUrlDialog,
        icon: const Icon(Icons.add),
        label: const Text('Add URL'),
      ),
    );
  }

  Widget _buildServerStatus() {
    final discovery = widget.serverDiscovery;
    final server = discovery.primaryServer;

    // Determine display text
    String title;
    String subtitle;
    if (discovery.hasConfiguredUrl) {
      title = 'Server: ${discovery.configuredUrl}';
      subtitle = discovery.hasServers ? 'Connected' : 'Configured (tap to change)';
    } else if (discovery.hasServers) {
      title = 'Connected to ${server!.host}';
      subtitle = server.isManualUrl ? server.configuredUrl ?? '' : 'Port ${server.port}';
    } else {
      title = 'No server configured';
      subtitle = 'Tap to set server URL';
    }

    return ListTile(
      leading: Icon(
        discovery.hasServers ? Icons.cloud_done : Icons.cloud_off,
        color: discovery.hasServers ? Colors.green : Colors.grey,
      ),
      title: Text(title),
      subtitle: Text(subtitle),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (discovery.isDiscovering)
            const SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          else
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: () {
                discovery.stopDiscovery();
                discovery.startDiscovery();
              },
              tooltip: 'Search local network',
            ),
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: _showServerSettingsDialog,
            tooltip: 'Server settings',
          ),
        ],
      ),
      onTap: _showServerSettingsDialog,
    );
  }

  void _showServerSettingsDialog() {
    final controller = TextEditingController(
      text: widget.serverDiscovery.configuredUrl ?? '',
    );

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Server Settings'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Enter the URL of your Claudsidian server:',
              style: TextStyle(fontSize: 14),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                hintText: 'https://claudsidian.example.com',
                labelText: 'Server URL',
                helperText: 'Or use IP:port like 192.168.1.100:8765',
                border: OutlineInputBorder(),
              ),
              autofocus: true,
              keyboardType: TextInputType.url,
            ),
            const SizedBox(height: 16),
            Text(
              'Leave empty to use automatic discovery on local network.',
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey.shade600,
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          if (widget.serverDiscovery.hasConfiguredUrl)
            TextButton(
              onPressed: () {
                widget.serverDiscovery.setServerUrl(null);
                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Server URL cleared')),
                );
              },
              child: const Text('Clear'),
            ),
          FilledButton(
            onPressed: () {
              final url = controller.text.trim();
              widget.serverDiscovery.setServerUrl(url.isEmpty ? null : url);
              Navigator.pop(context);
              if (url.isNotEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Server set to: $url')),
                );
              }
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  Widget _buildSyncStatus() {
    final sync = widget.syncService;
    final queue = widget.urlQueue;

    String statusText;
    Color statusColor;

    switch (sync.status) {
      case SyncStatus.idle:
        statusText = 'Ready';
        statusColor = Colors.green;
        break;
      case SyncStatus.syncing:
        statusText = 'Syncing...';
        statusColor = Colors.blue;
        break;
      case SyncStatus.noServer:
        statusText = 'Waiting for server';
        statusColor = Colors.orange;
        break;
      case SyncStatus.error:
        statusText = 'Error: ${sync.lastError}';
        statusColor = Colors.red;
        break;
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          Container(
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              color: statusColor,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              statusText,
              style: TextStyle(color: statusColor),
            ),
          ),
          Text(
            '${queue.pendingCount} pending',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  Widget _buildQueueList() {
    final items = widget.urlQueue.items;

    if (items.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.inbox,
              size: 64,
              color: Colors.grey.shade400,
            ),
            const SizedBox(height: 16),
            Text(
              'No URLs in queue',
              style: TextStyle(
                color: Colors.grey.shade600,
                fontSize: 16,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Share a URL from any app to capture it',
              style: TextStyle(
                color: Colors.grey.shade500,
                fontSize: 14,
              ),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      itemCount: items.length,
      itemBuilder: (context, index) {
        final item = items[index];
        return _buildQueueItem(item);
      },
    );
  }

  Widget _buildQueueItem(QueuedUrl item) {
    IconData statusIcon;
    Color statusColor;

    switch (item.status) {
      case QueuedUrlStatus.pending:
        statusIcon = Icons.schedule;
        statusColor = Colors.orange;
        break;
      case QueuedUrlStatus.sending:
        statusIcon = Icons.sync;
        statusColor = Colors.blue;
        break;
      case QueuedUrlStatus.sent:
        statusIcon = Icons.check_circle;
        statusColor = Colors.green;
        break;
      case QueuedUrlStatus.failed:
        statusIcon = Icons.error;
        statusColor = Colors.red;
        break;
    }

    return Dismissible(
      key: Key(item.id),
      direction: DismissDirection.endToStart,
      background: Container(
        color: Colors.red,
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 16),
        child: const Icon(Icons.delete, color: Colors.white),
      ),
      onDismissed: (_) => widget.urlQueue.remove(item.id),
      child: ListTile(
        leading: Icon(statusIcon, color: statusColor),
        title: Text(
          item.url,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        subtitle: Text(
          item.status == QueuedUrlStatus.failed && item.lastError != null
              ? item.lastError!
              : _formatTime(item.addedAt),
          style: TextStyle(
            color: item.status == QueuedUrlStatus.failed
                ? Colors.red
                : Colors.grey,
          ),
        ),
        trailing: item.status == QueuedUrlStatus.failed
            ? IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: () =>
                    widget.urlQueue.updateStatus(item.id, QueuedUrlStatus.pending),
              )
            : null,
      ),
    );
  }

  String _formatTime(DateTime time) {
    final now = DateTime.now();
    final diff = now.difference(time);

    if (diff.inMinutes < 1) {
      return 'Just now';
    } else if (diff.inHours < 1) {
      return '${diff.inMinutes}m ago';
    } else if (diff.inDays < 1) {
      return '${diff.inHours}h ago';
    } else {
      return '${diff.inDays}d ago';
    }
  }

  void _showAddUrlDialog() {
    final controller = TextEditingController();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add URL'),
        content: TextField(
          controller: controller,
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
          TextButton(
            onPressed: () {
              final url = controller.text.trim();
              if (url.isNotEmpty) {
                widget.urlQueue.addUrl(url);
                Navigator.pop(context);
              }
            },
            child: const Text('Add'),
          ),
        ],
      ),
    );
  }
}
