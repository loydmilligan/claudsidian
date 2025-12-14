/// Model for a queued URL waiting to be sent to the server.
library;

import 'package:json_annotation/json_annotation.dart';

part 'queued_url.g.dart';

/// Status of a queued URL.
enum QueuedUrlStatus {
  /// Waiting to be sent
  pending,

  /// Currently being sent
  sending,

  /// Successfully sent to server
  sent,

  /// Failed to send
  failed,
}

/// A URL queued for sending to the Claudsidian server.
@JsonSerializable()
class QueuedUrl {
  /// Unique identifier for this queue entry
  final String id;

  /// The URL to capture
  final String url;

  /// When the URL was added to the queue
  final DateTime addedAt;

  /// Current status of this queue entry
  QueuedUrlStatus status;

  /// Number of times we've tried to send this URL
  int attempts;

  /// Error message from last failed attempt
  String? lastError;

  /// When the URL was last attempted
  DateTime? lastAttemptAt;

  /// Create a new queued URL entry.
  QueuedUrl({
    required this.id,
    required this.url,
    required this.addedAt,
    this.status = QueuedUrlStatus.pending,
    this.attempts = 0,
    this.lastError,
    this.lastAttemptAt,
  });

  /// Create a new queued URL with auto-generated ID.
  factory QueuedUrl.create(String url) {
    return QueuedUrl(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      url: url,
      addedAt: DateTime.now(),
    );
  }

  /// Create from JSON map.
  factory QueuedUrl.fromJson(Map<String, dynamic> json) =>
      _$QueuedUrlFromJson(json);

  /// Convert to JSON map.
  Map<String, dynamic> toJson() => _$QueuedUrlToJson(this);

  /// Mark as currently sending.
  void markSending() {
    status = QueuedUrlStatus.sending;
    attempts++;
    lastAttemptAt = DateTime.now();
    lastError = null;
  }

  /// Mark as successfully sent.
  void markSent() {
    status = QueuedUrlStatus.sent;
    lastError = null;
  }

  /// Mark as failed with error message.
  void markFailed(String error) {
    status = QueuedUrlStatus.failed;
    lastError = error;
  }

  /// Reset to pending status for retry.
  void resetToPending() {
    status = QueuedUrlStatus.pending;
  }
}
