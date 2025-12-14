/// History tab showing recent captures.
library;

import 'package:flutter/material.dart';
import '../services/capture_history.dart';
import '../models/capture_result.dart';
import '../theme/app_theme.dart';

/// Tab showing capture history.
class HistoryTab extends StatefulWidget {
  final CaptureHistoryService captureHistory;

  const HistoryTab({
    super.key,
    required this.captureHistory,
  });

  @override
  State<HistoryTab> createState() => _HistoryTabState();
}

class _HistoryTabState extends State<HistoryTab> {
  @override
  void initState() {
    super.initState();
    widget.captureHistory.addListener(_onChanged);
  }

  @override
  void dispose() {
    widget.captureHistory.removeListener(_onChanged);
    super.dispose();
  }

  void _onChanged() {
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final history = widget.captureHistory.history;
    final todaysCaptures = widget.captureHistory.todaysCaptures;
    final capturesByType = widget.captureHistory.capturesByType;

    if (history.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.history,
              size: 64,
              color: Theme.of(context).colorScheme.primary.withOpacity(0.5),
            ),
            const SizedBox(height: 16),
            Text(
              'No captures yet',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              'Share URLs from any app to get started',
              style: TextStyle(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      );
    }

    return CustomScrollView(
      slivers: [
        // Summary header
        SliverToBoxAdapter(
          child: Container(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                _buildSummaryCard(
                  context,
                  'Today',
                  todaysCaptures.length.toString(),
                  Icons.today,
                ),
                const SizedBox(width: 12),
                _buildSummaryCard(
                  context,
                  'Total',
                  history.length.toString(),
                  Icons.history,
                ),
              ],
            ),
          ),
        ),

        // Type breakdown
        SliverToBoxAdapter(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              children: capturesByType.entries.map((entry) {
                return Chip(
                  avatar: Text(entry.key.emoji),
                  label: Text('${entry.key.displayName}: ${entry.value.length}'),
                  visualDensity: VisualDensity.compact,
                );
              }).toList(),
            ),
          ),
        ),

        const SliverToBoxAdapter(child: SizedBox(height: 16)),

        // Capture list
        SliverList(
          delegate: SliverChildBuilderDelegate(
            (context, index) {
              final capture = history[index];
              return _buildCaptureItem(capture);
            },
            childCount: history.length,
          ),
        ),

        // Bottom padding
        const SliverToBoxAdapter(child: SizedBox(height: 80)),
      ],
    );
  }

  Widget _buildSummaryCard(
    BuildContext context,
    String label,
    String value,
    IconData icon,
  ) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Icon(icon, size: 24),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    value,
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  Text(
                    label,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCaptureItem(CaptureResult capture) {
    return ListTile(
      leading: ContentTypeBadge(
        type: capture.contentType.name,
        showEmoji: true,
      ),
      title: Text(
        capture.title,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: Row(
        children: [
          Text(
            _formatTime(capture.capturedAt),
            style: const TextStyle(fontSize: 12),
          ),
          if (capture.researchSubject != null) ...[
            const Text(' \u2022 ', style: TextStyle(fontSize: 12)),
            Flexible(
              child: Text(
                capture.researchSubject!,
                style: TextStyle(
                  fontSize: 12,
                  color: Theme.of(context).colorScheme.primary,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
          if (capture.quickCapture) ...[
            const Text(' \u2022 ', style: TextStyle(fontSize: 12)),
            const Text(
              'Quick',
              style: TextStyle(fontSize: 12, fontStyle: FontStyle.italic),
            ),
          ],
        ],
      ),
      trailing: PopupMenuButton(
        itemBuilder: (context) => [
          const PopupMenuItem(
            value: 'copy',
            child: Row(
              children: [
                Icon(Icons.copy, size: 20),
                SizedBox(width: 8),
                Text('Copy URL'),
              ],
            ),
          ),
          const PopupMenuItem(
            value: 'remove',
            child: Row(
              children: [
                Icon(Icons.delete, size: 20),
                SizedBox(width: 8),
                Text('Remove'),
              ],
            ),
          ),
        ],
        onSelected: (value) {
          if (value == 'copy') {
            // Copy URL to clipboard
            // Clipboard.setData(ClipboardData(text: capture.url));
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('URL copied')),
            );
          } else if (value == 'remove') {
            widget.captureHistory.removeCapture(capture.url);
          }
        },
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
    } else if (diff.inDays < 7) {
      return '${diff.inDays}d ago';
    } else {
      return '${time.month}/${time.day}';
    }
  }
}
