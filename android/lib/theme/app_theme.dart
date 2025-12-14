/// App theme configuration with dark mode support.
library;

import 'package:flutter/material.dart';

/// App theme configuration.
class AppTheme {
  // Brand colors
  static const Color primaryColor = Color(0xFF7C3AED); // Purple
  static const Color secondaryColor = Color(0xFF6D28D9);

  // Content type colors
  static const Map<String, Color> contentTypeColors = {
    'article': Color(0xFF3B82F6),    // Blue
    'video': Color(0xFFEF4444),      // Red
    'repository': Color(0xFF10B981), // Green
    'news': Color(0xFFF59E0B),       // Amber
    'walkthrough': Color(0xFF8B5CF6), // Violet
    'printable': Color(0xFFEC4899),  // Pink
    'unknown': Color(0xFF6B7280),    // Gray
  };

  /// Get color for content type.
  static Color getContentTypeColor(String type) {
    return contentTypeColors[type.toLowerCase()] ?? contentTypeColors['unknown']!;
  }

  /// Light theme.
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primaryColor,
        brightness: Brightness.light,
      ),
      appBarTheme: const AppBarTheme(
        centerTitle: true,
        elevation: 0,
      ),
      cardTheme: CardTheme(
        elevation: 1,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        filled: true,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
      ),
      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        elevation: 4,
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
    );
  }

  /// Dark theme.
  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primaryColor,
        brightness: Brightness.dark,
      ),
      appBarTheme: const AppBarTheme(
        centerTitle: true,
        elevation: 0,
      ),
      cardTheme: CardTheme(
        elevation: 2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        filled: true,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
      ),
      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        elevation: 4,
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
    );
  }
}

/// Content type badge widget.
class ContentTypeBadge extends StatelessWidget {
  final String type;
  final bool showEmoji;
  final double fontSize;

  const ContentTypeBadge({
    super.key,
    required this.type,
    this.showEmoji = true,
    this.fontSize = 11,
  });

  @override
  Widget build(BuildContext context) {
    final color = AppTheme.getContentTypeColor(type);
    final displayName = _getDisplayName(type);
    final emoji = _getEmoji(type);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Text(
        showEmoji ? '$emoji $displayName' : displayName,
        style: TextStyle(
          fontSize: fontSize,
          color: color,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  String _getDisplayName(String type) {
    switch (type.toLowerCase()) {
      case 'article':
        return 'Article';
      case 'video':
        return 'Video';
      case 'repository':
        return 'Repo';
      case 'news':
        return 'News';
      case 'walkthrough':
        return 'Guide';
      case 'printable':
        return '3D';
      default:
        return type;
    }
  }

  String _getEmoji(String type) {
    switch (type.toLowerCase()) {
      case 'article':
        return '\u{1F4DD}';
      case 'video':
        return '\u{1F3AC}';
      case 'repository':
        return '\u{1F4BB}';
      case 'news':
        return '\u{1F4F0}';
      case 'walkthrough':
        return '\u{1F4D6}';
      case 'printable':
        return '\u{1F5A8}';
      default:
        return '\u{2753}';
    }
  }
}
