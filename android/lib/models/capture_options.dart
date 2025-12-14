/// Model for capture options and attachments.
library;

import 'dart:typed_data';

/// Options for capturing a URL.
class CaptureOptions {
  /// Model to use for AI processing (null = default).
  final String? model;

  /// Temperature for AI generation (0.0-1.0).
  final double? temperature;

  /// Research subject to add note to.
  final String? researchSubject;

  /// Skip AI processing (quick capture / inbox mode).
  final bool skipAi;

  /// User note to attach.
  final String? userNote;

  /// Image attachment (as bytes).
  final Uint8List? imageData;

  /// Image MIME type (e.g., 'image/jpeg').
  final String? imageMimeType;

  /// Audio attachment (as bytes).
  final Uint8List? audioData;

  /// Audio MIME type (e.g., 'audio/m4a').
  final String? audioMimeType;

  CaptureOptions({
    this.model,
    this.temperature,
    this.researchSubject,
    this.skipAi = false,
    this.userNote,
    this.imageData,
    this.imageMimeType,
    this.audioData,
    this.audioMimeType,
  });

  /// Create default options.
  factory CaptureOptions.defaults() => CaptureOptions();

  /// Create quick capture options (no AI).
  factory CaptureOptions.quick() => CaptureOptions(skipAi: true);

  /// Whether this has any attachments.
  bool get hasAttachments =>
      userNote != null || imageData != null || audioData != null;

  /// Convert to JSON for API request.
  Map<String, dynamic> toJson() {
    final json = <String, dynamic>{
      'source': 'mobile',
    };

    if (skipAi) {
      json['skip_ai'] = true;
    } else {
      if (model != null) {
        json['model'] = model;
      }
      if (temperature != null) {
        json['temperature'] = temperature;
      }
    }

    if (researchSubject != null) {
      json['research_subject'] = researchSubject;
    }

    if (userNote != null) {
      json['user_note'] = userNote;
    }

    // Note: image and audio are sent separately as multipart
    // This JSON is for the main capture request body

    return json;
  }

  /// Copy with modifications.
  CaptureOptions copyWith({
    String? model,
    double? temperature,
    String? researchSubject,
    bool? skipAi,
    String? userNote,
    Uint8List? imageData,
    String? imageMimeType,
    Uint8List? audioData,
    String? audioMimeType,
  }) {
    return CaptureOptions(
      model: model ?? this.model,
      temperature: temperature ?? this.temperature,
      researchSubject: researchSubject ?? this.researchSubject,
      skipAi: skipAi ?? this.skipAi,
      userNote: userNote ?? this.userNote,
      imageData: imageData ?? this.imageData,
      imageMimeType: imageMimeType ?? this.imageMimeType,
      audioData: audioData ?? this.audioData,
      audioMimeType: audioMimeType ?? this.audioMimeType,
    );
  }
}
