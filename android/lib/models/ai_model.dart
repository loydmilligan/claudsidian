/// Model for AI models available on the server.
library;

/// Information about an AI model available for capture.
class AIModel {
  /// Model ID (e.g., 'x-ai/grok-4.1-fast').
  final String id;

  /// Display name for the model.
  final String name;

  /// Number of captures using this model.
  final int captures;

  /// Average cost per capture in USD.
  final double? avgCost;

  /// Average user rating (1-5).
  final double? avgRating;

  /// Whether this is the default model.
  final bool isDefault;

  AIModel({
    required this.id,
    required this.name,
    this.captures = 0,
    this.avgCost,
    this.avgRating,
    this.isDefault = false,
  });

  /// Create from server JSON response.
  factory AIModel.fromJson(Map<String, dynamic> json, {bool isDefault = false}) {
    return AIModel(
      id: json['id'] ?? '',
      name: json['name'] ?? json['id'] ?? 'Unknown',
      captures: json['captures'] ?? 0,
      avgCost: json['avg_cost']?.toDouble(),
      avgRating: json['avg_rating']?.toDouble(),
      isDefault: isDefault,
    );
  }

  /// Get short display name (last part after /).
  String get shortName {
    final parts = name.split('/');
    return parts.last;
  }

  /// Get stats string for display.
  String get statsString {
    final stats = <String>[];
    if (avgCost != null && avgCost! > 0) {
      stats.add('\$${avgCost!.toStringAsFixed(4)}/cap');
    }
    if (avgRating != null) {
      stats.add('${avgRating!.toStringAsFixed(1)}\u2605');
    }
    if (captures > 0) {
      stats.add('$captures uses');
    }
    return stats.join(' \u00B7 ');
  }
}

/// Response from /models endpoint.
class ModelsResponse {
  /// Available models.
  final List<AIModel> models;

  /// Default model ID.
  final String? defaultModel;

  ModelsResponse({
    required this.models,
    this.defaultModel,
  });

  /// Create from server JSON response.
  factory ModelsResponse.fromJson(Map<String, dynamic> json) {
    final defaultModelId = json['default_model'];
    final modelsList = (json['models'] as List?)
            ?.map((m) => AIModel.fromJson(
                  m as Map<String, dynamic>,
                  isDefault: m['id'] == defaultModelId,
                ))
            .toList() ??
        [];

    return ModelsResponse(
      models: modelsList,
      defaultModel: defaultModelId,
    );
  }

  /// Get the default model.
  AIModel? get defaultModelInfo {
    if (defaultModel == null) return null;
    return models.cast<AIModel?>().firstWhere(
          (m) => m?.id == defaultModel,
          orElse: () => null,
        );
  }
}
