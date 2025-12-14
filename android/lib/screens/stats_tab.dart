/// Stats tab showing capture statistics and dashboard.
library;

import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/capture_history.dart';
import '../models/capture_result.dart';
import '../theme/app_theme.dart';

/// Tab showing capture statistics.
class StatsTab extends StatefulWidget {
  final ApiService apiService;
  final CaptureHistoryService captureHistory;

  const StatsTab({
    super.key,
    required this.apiService,
    required this.captureHistory,
  });

  @override
  State<StatsTab> createState() => _StatsTabState();
}

class _StatsTabState extends State<StatsTab> {
  Map<String, dynamic>? _serverStats;
  bool _loadingStats = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    widget.captureHistory.addListener(_onChanged);
    _loadServerStats();
  }

  @override
  void dispose() {
    widget.captureHistory.removeListener(_onChanged);
    super.dispose();
  }

  void _onChanged() {
    if (mounted) setState(() {});
  }

  Future<void> _loadServerStats() async {
    if (!widget.apiService.isConnected) return;

    setState(() {
      _loadingStats = true;
      _error = null;
    });

    try {
      _serverStats = await widget.apiService.getStats();
    } catch (e) {
      _error = e.toString();
    }

    if (mounted) {
      setState(() => _loadingStats = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final history = widget.captureHistory.history;
    final todaysCaptures = widget.captureHistory.todaysCaptures;
    final thisWeeksCaptures = widget.captureHistory.thisWeeksCaptures;
    final capturesByType = widget.captureHistory.capturesByType;

    return RefreshIndicator(
      onRefresh: _loadServerStats,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Local stats section
          Text(
            'Your Activity',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 12),

          // Summary cards
          Row(
            children: [
              _buildStatCard(
                context,
                'Today',
                todaysCaptures.length.toString(),
                Icons.today,
                Colors.blue,
              ),
              const SizedBox(width: 12),
              _buildStatCard(
                context,
                'This Week',
                thisWeeksCaptures.length.toString(),
                Icons.date_range,
                Colors.green,
              ),
              const SizedBox(width: 12),
              _buildStatCard(
                context,
                'Total',
                history.length.toString(),
                Icons.history,
                Colors.purple,
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Content type breakdown
          Text(
            'By Content Type',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 12),

          if (capturesByType.isEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Center(
                  child: Text(
                    'No captures yet',
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                ),
              ),
            )
          else
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: capturesByType.entries.map((entry) {
                    final percentage = (entry.value.length / history.length * 100);
                    return _buildTypeBar(
                      context,
                      entry.key,
                      entry.value.length,
                      percentage,
                    );
                  }).toList(),
                ),
              ),
            ),
          const SizedBox(height: 24),

          // Server stats section
          Row(
            children: [
              Text(
                'Server Statistics',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const Spacer(),
              if (_loadingStats)
                const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
            ],
          ),
          const SizedBox(height: 12),

          if (!widget.apiService.isConnected)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  children: [
                    Icon(
                      Icons.cloud_off,
                      size: 48,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'Not connected to server',
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
            )
          else if (_error != null)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  children: [
                    Icon(
                      Icons.error_outline,
                      size: 48,
                      color: Theme.of(context).colorScheme.error,
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'Failed to load stats',
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                    const SizedBox(height: 8),
                    FilledButton.tonal(
                      onPressed: _loadServerStats,
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              ),
            )
          else if (_serverStats != null)
            _buildServerStats()
          else
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  children: [
                    const CircularProgressIndicator(),
                    const SizedBox(height: 12),
                    Text(
                      'Loading server stats...',
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
            ),

          const SizedBox(height: 80),
        ],
      ),
    );
  }

  Widget _buildStatCard(
    BuildContext context,
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            children: [
              Icon(icon, color: color, size: 28),
              const SizedBox(height: 8),
              Text(
                value,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
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
        ),
      ),
    );
  }

  Widget _buildTypeBar(
    BuildContext context,
    ContentType type,
    int count,
    double percentage,
  ) {
    final color = AppTheme.getContentTypeColor(type.name);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          SizedBox(
            width: 80,
            child: Row(
              children: [
                Text(type.emoji),
                const SizedBox(width: 6),
                Text(
                  type.displayName,
                  style: const TextStyle(fontSize: 13),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Stack(
              children: [
                Container(
                  height: 20,
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(4),
                  ),
                ),
                FractionallySizedBox(
                  widthFactor: percentage / 100,
                  child: Container(
                    height: 20,
                    decoration: BoxDecoration(
                      color: color,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          SizedBox(
            width: 40,
            child: Text(
              '$count',
              textAlign: TextAlign.right,
              style: const TextStyle(
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildServerStats() {
    final stats = _serverStats!;

    // Extract available stats
    final totalCaptures = stats['total_captures'] ?? 0;
    final totalCost = stats['total_cost'] ?? 0.0;
    final avgCost = stats['avg_cost'] ?? 0.0;
    final modelStats = stats['model_stats'] as Map<String, dynamic>? ?? {};

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Total captures and cost
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Total Captures',
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                          fontSize: 12,
                        ),
                      ),
                      Text(
                        '$totalCaptures',
                        style: Theme.of(context).textTheme.headlineMedium,
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Total Cost',
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                          fontSize: 12,
                        ),
                      ),
                      Text(
                        '\$${(totalCost as num).toStringAsFixed(4)}',
                        style: Theme.of(context).textTheme.headlineMedium,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Avg cost per capture: \$${(avgCost as num).toStringAsFixed(5)}',
              style: TextStyle(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
                fontSize: 12,
              ),
            ),

            if (modelStats.isNotEmpty) ...[
              const Divider(height: 24),
              Text(
                'By Model',
                style: Theme.of(context).textTheme.titleSmall,
              ),
              const SizedBox(height: 8),
              ...modelStats.entries.map((entry) {
                final name = entry.key.split('/').last;
                final data = entry.value as Map<String, dynamic>;
                final captures = data['captures'] ?? 0;
                final cost = data['total_cost'] ?? 0.0;
                final rating = data['avg_rating'];

                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          name,
                          style: const TextStyle(fontSize: 13),
                        ),
                      ),
                      Text(
                        '$captures',
                        style: const TextStyle(fontSize: 13),
                      ),
                      const SizedBox(width: 12),
                      Text(
                        '\$${(cost as num).toStringAsFixed(4)}',
                        style: const TextStyle(fontSize: 13),
                      ),
                      if (rating != null) ...[
                        const SizedBox(width: 12),
                        Text(
                          '${(rating as num).toStringAsFixed(1)}\u2605',
                          style: TextStyle(
                            fontSize: 13,
                            color: Colors.amber.shade700,
                          ),
                        ),
                      ],
                    ],
                  ),
                );
              }),
            ],
          ],
        ),
      ),
    );
  }
}
