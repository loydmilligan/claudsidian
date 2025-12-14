/// Share handler service for receiving URLs from other Android apps.
///
/// This service listens for share intents and adds shared URLs to the
/// local queue for processing.
library;

import 'dart:async';
import 'package:receive_sharing_intent/receive_sharing_intent.dart';
import 'url_queue.dart';

/// Handles incoming share intents from other Android apps.
///
/// When the user shares a URL to Claudsidian, this service captures it
/// and adds it to the local queue for later sync with the desktop server.
class ShareHandler {
  final UrlQueue _urlQueue;

  StreamSubscription? _intentSubscription;

  /// Create a new share handler.
  ///
  /// [urlQueue] - The queue to add shared URLs to
  ShareHandler({required UrlQueue urlQueue}) : _urlQueue = urlQueue;

  /// Start listening for share intents.
  ///
  /// Must be called after the app is initialized.
  void startListening() {
    try {
      // Handle share intents while app is running
      _intentSubscription = ReceiveSharingIntent.instance.getMediaStream().listen(
        (List<SharedMediaFile> files) {
          _handleSharedMedia(files);
        },
        onError: (error) {
          print('Error receiving shared URLs: $error');
        },
      );

      // Handle initial share intent (app was opened via share)
      ReceiveSharingIntent.instance.getInitialMedia().then((List<SharedMediaFile> files) {
        if (files.isNotEmpty) {
          _handleSharedMedia(files);
          // Clear the initial media to prevent re-processing
          ReceiveSharingIntent.instance.reset();
        }
      }).catchError((error) {
        print('Error getting initial media: $error');
      });
    } catch (e) {
      print('Error setting up share handler: $e');
    }
  }

  /// Process shared media by extracting URLs and adding them to the queue.
  void _handleSharedMedia(List<SharedMediaFile> files) {
    for (final file in files) {
      // SharedMediaFile path contains the shared text/URL
      String? urlString = file.path;

      // Also check message field for some share types
      if (urlString.isEmpty && file.message != null) {
        urlString = file.message;
      }

      if (urlString == null || urlString.isEmpty) continue;

      // Extract URL if it's embedded in text
      final urlMatch = RegExp(r'https?://[^\s]+').firstMatch(urlString);
      if (urlMatch != null) {
        urlString = urlMatch.group(0)!;
      }

      // Skip if not a valid URL
      if (!urlString.startsWith('http://') && !urlString.startsWith('https://')) {
        print('Skipping non-URL share: $urlString');
        continue;
      }

      // Add to queue
      _urlQueue.addUrl(urlString);
      print('Shared URL queued: $urlString');
    }
  }

  /// Stop listening and clean up resources.
  void dispose() {
    _intentSubscription?.cancel();
  }
}
