/// Model for capture result from the server.
library;

/// Content types supported by Claudsidian.
enum ContentType {
  article,
  video,
  repository,
  news,
  walkthrough,
  printable,
  unknown;

  /// Get display name for the content type.
  String get displayName {
    switch (this) {
      case ContentType.article:
        return 'Article';
      case ContentType.video:
        return 'Video';
      case ContentType.repository:
        return 'Repo';
      case ContentType.news:
        return 'News';
      case ContentType.walkthrough:
        return 'Guide';
      case ContentType.printable:
        return '3D Model';
      case ContentType.unknown:
        return 'Unknown';
    }
  }

  /// Get emoji for the content type.
  String get emoji {
    switch (this) {
      case ContentType.article:
        return '\u{1F4DD}'; // memo
      case ContentType.video:
        return '\u{1F3AC}'; // clapper board
      case ContentType.repository:
        return '\u{1F4BB}'; // laptop
      case ContentType.news:
        return '\u{1F4F0}'; // newspaper
      case ContentType.walkthrough:
        return '\u{1F4D6}'; // open book
      case ContentType.printable:
        return '\u{1F5A8}'; // printer
      case ContentType.unknown:
        return '\u{2753}'; // question mark
    }
  }

  /// Parse content type from server response.
  static ContentType fromString(String? type) {
    if (type == null) return ContentType.unknown;
    switch (type.toLowerCase()) {
      case 'article':
        return ContentType.article;
      case 'video':
        return ContentType.video;
      case 'repository':
      case 'repo':
        return ContentType.repository;
      case 'news':
        return ContentType.news;
      case 'walkthrough':
      case 'guide':
        return ContentType.walkthrough;
      case 'printable':
      case '3d-model':
        return ContentType.printable;
      default:
        return ContentType.unknown;
    }
  }
}

/// Result from a successful capture.
class CaptureResult {
  /// Title of the captured note.
  final String title;

  /// Path where note was saved.
  final String notePath;

  /// Content type detected.
  final ContentType contentType;

  /// Original URL captured.
  final String url;

  /// When the capture was completed.
  final DateTime capturedAt;

  /// Model used for summary (if any).
  final String? model;

  /// Research subject (if assigned).
  final String? researchSubject;

  /// Whether this was a quick capture (no AI).
  final bool quickCapture;

  CaptureResult({
    required this.title,
    required this.notePath,
    required this.contentType,
    required this.url,
    required this.capturedAt,
    this.model,
    this.researchSubject,
    this.quickCapture = false,
  });

  /// Create from server JSON response.
  factory CaptureResult.fromJson(Map<String, dynamic> json, String url) {
    return CaptureResult(
      title: json['title'] ?? 'Untitled',
      notePath: json['note_path'] ?? '',
      contentType: ContentType.fromString(json['type']),
      url: url,
      capturedAt: DateTime.now(),
      model: json['model'],
      researchSubject: json['research_subject'],
      quickCapture: json['quick'] ?? false,
    );
  }

  /// Convert to JSON for storage.
  Map<String, dynamic> toJson() => {
        'title': title,
        'note_path': notePath,
        'type': contentType.name,
        'url': url,
        'captured_at': capturedAt.toIso8601String(),
        'model': model,
        'research_subject': researchSubject,
        'quick_capture': quickCapture,
      };

  /// Create from stored JSON.
  factory CaptureResult.fromStoredJson(Map<String, dynamic> json) {
    return CaptureResult(
      title: json['title'] ?? 'Untitled',
      notePath: json['note_path'] ?? '',
      contentType: ContentType.fromString(json['type']),
      url: json['url'] ?? '',
      capturedAt: DateTime.parse(json['captured_at']),
      model: json['model'],
      researchSubject: json['research_subject'],
      quickCapture: json['quick_capture'] ?? false,
    );
  }
}
