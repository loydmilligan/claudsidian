/// Queue tab showing pending URLs.
library;

import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/capture_history.dart';
import '../services/url_queue.dart';
import '../models/queued_url.dart';
import '../theme/app_theme.dart';

/// Tab showing queued URLs waiting to be sent.
class QueueTab extends StatefulWidget {
  final ApiService apiService;
  final CaptureHistoryService captureHistory;

  const QueueTab({
    super.key,
    required this.apiService,
    required this.captureHistory,
  });

  @override
  State<QueueTab> createState() => _QueueTabState();
}

class _QueueTabState extends State<QueueTab> {
  final UrlQueue _queue = UrlQueue();
  bool _initialized = false;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    await _queue.load();
    _queue.addListener(_onQueueChanged);
    setState(() => _initialized = true);
  }

  void _onQueueChanged() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _queue.removeListener(_onQueueChanged);
    super.dispose();
  }

  Future<void> _syncAll() async {
    if (!widget.apiService.isConnected) return;

    final pending = _queue.items
        .where((item) =>
            item.status == QueuedUrlStatus.pending ||
            item.status == QueuedUrlStatus.failed)
        .toList();

    for (final item in pending) {
      await _syncItem(item);
    }
  }

  Future<void> _syncItem(QueuedUrl item) async {
    _queue.updateStatus(item.id, QueuedUrlStatus.sending);

    try {
      final result = await widget.apiService.capture(item.url);
      await widget.captureHistory.addCapture(result);
      _queue.updateStatus(item.id, QueuedUrlStatus.sent);

      // Remove after short delay
      await Future.delayed(const Duration(seconds: 1));
      _queue.remove(item.id);
    } catch (e) {
      _queue.markFailed(item.id, e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_initialized) {
      return const Center(child: CircularProgressIndicator());
    }

    final items = _queue.items;
    final pendingCount = items
        .where((i) =>
            i.status == QueuedUrlStatus.pending ||
            i.status == QueuedUrlStatus.failed)
        .length;
    final isConnected = widget.apiService.isConnected;

    if (items.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              isConnected ? Icons.check_circle : Icons.cloud_sync,
              size: 64,
              color: isConnected
                  ? Colors.green
                  : Theme.of(context).colorScheme.primary,
            ),
            const SizedBox(height: 16),
            Text(
              isConnected ? 'Ready!' : 'Waiting for server',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              'Queue is empty',
              style: TextStyle(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 24),
            Text(
              isConnected
                  ? 'Share URLs from any app to capture them'
                  : 'Configure server, then share URLs',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      );
    }

    return Column(
      children: [
        // Sync bar
        if (pendingCount > 0 && isConnected)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            color: Theme.of(context).colorScheme.primaryContainer,
            child: Row(
              children: [
                Text(
                  '$pendingCount pending',
                  style: TextStyle(
                    color: Theme.of(context).colorScheme.onPrimaryContainer,
                  ),
                ),
                const Spacer(),
                FilledButton.tonal(
                  onPressed: _syncAll,
                  child: const Text('Sync All'),
                ),
              ],
            ),
          ),

        // Queue list
        Expanded(
          child: ListView.builder(
            itemCount: items.length,
            itemBuilder: (context, index) {
              final item = items[index];
              return _buildQueueItem(item);
            },
          ),
        ),
      ],
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
      onDismissed: (_) => _queue.remove(item.id),
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
                : Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
        trailing: item.status == QueuedUrlStatus.failed
            ? IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: () =>
                    _queue.updateStatus(item.id, QueuedUrlStatus.pending),
              )
            : item.status == QueuedUrlStatus.pending &&
                    widget.apiService.isConnected
                ? IconButton(
                    icon: const Icon(Icons.send),
                    onPressed: () => _syncItem(item),
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
}
