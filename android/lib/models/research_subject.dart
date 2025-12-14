/// Model for research subjects.
library;

/// A research subject for organizing captures.
class ResearchSubject {
  /// Subject name (used as folder name).
  final String name;

  /// Display name (name with dashes replaced by spaces).
  String get displayName => name.replaceAll('-', ' ');

  /// Number of notes in this subject.
  final int noteCount;

  /// Whether the wizard setup is complete.
  final bool hasWizardComplete;

  /// Research goal (if set).
  final String? goal;

  ResearchSubject({
    required this.name,
    this.noteCount = 0,
    this.hasWizardComplete = true,
    this.goal,
  });

  /// Create from server JSON response.
  factory ResearchSubject.fromJson(Map<String, dynamic> json) {
    return ResearchSubject(
      name: json['name'] ?? '',
      noteCount: json['note_count'] ?? 0,
      hasWizardComplete: json['has_wizard_complete'] ?? true,
      goal: json['goal'],
    );
  }

  /// Get status badges for display.
  List<String> get badges {
    final result = <String>[];
    if (!hasWizardComplete) {
      result.add('\u2699\uFE0F setup pending');
    }
    if (noteCount > 0) {
      result.add('$noteCount notes');
    }
    return result;
  }

  /// Get full display with badges.
  String get displayWithBadges {
    if (badges.isEmpty) return displayName;
    return '$displayName (${badges.join(', ')})';
  }
}

/// Response from /subjects endpoint.
class SubjectsResponse {
  /// Available subjects.
  final List<ResearchSubject> subjects;

  SubjectsResponse({required this.subjects});

  /// Create from server JSON response.
  factory SubjectsResponse.fromJson(Map<String, dynamic> json) {
    final subjectsList = (json['subjects'] as List?)
            ?.map((s) => ResearchSubject.fromJson(s as Map<String, dynamic>))
            .toList() ??
        [];

    return SubjectsResponse(subjects: subjectsList);
  }
}
