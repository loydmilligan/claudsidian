/// Bottom sheet for capturing a URL with options.
library;

import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/capture_history.dart';
import '../models/capture_result.dart';
import '../models/capture_options.dart';
import '../models/ai_model.dart';
import '../models/research_subject.dart';

/// Bottom sheet for capturing a URL with options.
class CaptureSheet extends StatefulWidget {
  final String url;
  final ApiService apiService;
  final CaptureHistoryService captureHistory;
  final void Function(CaptureResult result)? onCaptured;

  const CaptureSheet({
    super.key,
    required this.url,
    required this.apiService,
    required this.captureHistory,
    this.onCaptured,
  });

  @override
  State<CaptureSheet> createState() => _CaptureSheetState();
}

class _CaptureSheetState extends State<CaptureSheet> {
  // Options
  String? _selectedModel;
  String? _selectedSubject;
  bool _quickCapture = false;
  double _temperature = 0.7;
  bool _showAdvanced = false;

  // Data
  ModelsResponse? _models;
  SubjectsResponse? _subjects;
  bool _loadingModels = true;
  bool _loadingSubjects = true;

  // Capture state
  bool _isCapturing = false;
  String? _error;

  // User note
  final _noteController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  @override
  void dispose() {
    _noteController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    if (!widget.apiService.isConnected) {
      setState(() {
        _loadingModels = false;
        _loadingSubjects = false;
      });
      return;
    }

    // Load models and subjects in parallel
    try {
      final results = await Future.wait([
        widget.apiService.getModels().catchError((_) => null),
        widget.apiService.getSubjects().catchError((_) => null),
      ]);

      if (mounted) {
        setState(() {
          _models = results[0] as ModelsResponse?;
          _subjects = results[1] as SubjectsResponse?;
          _loadingModels = false;
          _loadingSubjects = false;

          // Set default model
          if (_models?.defaultModel != null) {
            _selectedModel = _models!.defaultModel;
          }
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loadingModels = false;
          _loadingSubjects = false;
        });
      }
    }
  }

  Future<void> _capture() async {
    setState(() {
      _isCapturing = true;
      _error = null;
    });

    try {
      final options = CaptureOptions(
        model: _quickCapture ? null : _selectedModel,
        temperature: _quickCapture ? null : _temperature,
        researchSubject: _selectedSubject,
        skipAi: _quickCapture,
        userNote: _noteController.text.isNotEmpty ? _noteController.text : null,
      );

      final result = await widget.apiService.capture(widget.url, options: options);
      await widget.captureHistory.addCapture(result);

      if (mounted) {
        Navigator.pop(context);
        widget.onCaptured?.call(result);
      }
    } on DuplicateException catch (e) {
      setState(() {
        _error = 'Already captured: ${e.existingNote}';
        _isCapturing = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isCapturing = false;
      });
    }
  }

  Future<void> _createSubject() async {
    final controller = TextEditingController();

    final name = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('New Research Subject'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            hintText: 'e.g., Machine Learning Basics',
            labelText: 'Subject Name',
          ),
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('Create'),
          ),
        ],
      ),
    );

    if (name != null && name.isNotEmpty) {
      try {
        final subject = await widget.apiService.createSubject(name);
        setState(() {
          _selectedSubject = subject.name;
          // Reload subjects
          _loadingSubjects = true;
        });
        await _loadData();
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to create subject: $e')),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final isConnected = widget.apiService.isConnected;

    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Handle bar
          Center(
            child: Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.only(bottom: 16),
              decoration: BoxDecoration(
                color: colorScheme.onSurfaceVariant.withOpacity(0.4),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),

          // Title
          Text(
            'Capture URL',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),

          // URL display
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: colorScheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              widget.url,
              style: TextStyle(
                fontSize: 12,
                color: colorScheme.onSurfaceVariant,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(height: 16),

          if (!isConnected) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: colorScheme.errorContainer,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Icon(Icons.cloud_off, color: colorScheme.error),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'Not connected to server. Configure server in settings.',
                      style: TextStyle(color: colorScheme.onErrorContainer),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ] else ...[
            // Quick capture toggle
            SwitchListTile(
              value: _quickCapture,
              onChanged: (value) => setState(() => _quickCapture = value),
              title: const Text('Quick Capture'),
              subtitle: const Text('Skip AI processing'),
              dense: true,
              contentPadding: EdgeInsets.zero,
            ),

            // Model selection (if not quick capture)
            if (!_quickCapture) ...[
              const SizedBox(height: 8),
              _buildModelDropdown(),
            ],

            // Research subject
            const SizedBox(height: 16),
            _buildSubjectDropdown(),

            // User note
            const SizedBox(height: 16),
            TextField(
              controller: _noteController,
              decoration: const InputDecoration(
                labelText: 'Add a note (optional)',
                hintText: 'Personal context or comments...',
                border: OutlineInputBorder(),
              ),
              maxLines: 2,
            ),

            // Advanced options
            if (!_quickCapture) ...[
              const SizedBox(height: 8),
              InkWell(
                onTap: () => setState(() => _showAdvanced = !_showAdvanced),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: Row(
                    children: [
                      Icon(
                        _showAdvanced ? Icons.expand_less : Icons.expand_more,
                        size: 20,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        'Advanced',
                        style: TextStyle(
                          color: colorScheme.onSurfaceVariant,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              if (_showAdvanced) ...[
                Row(
                  children: [
                    const Text('Temperature:'),
                    Expanded(
                      child: Slider(
                        value: _temperature,
                        min: 0.0,
                        max: 1.0,
                        divisions: 10,
                        label: _temperature.toStringAsFixed(1),
                        onChanged: (value) => setState(() => _temperature = value),
                      ),
                    ),
                    Text(_temperature.toStringAsFixed(1)),
                  ],
                ),
              ],
            ],
          ],

          // Error display
          if (_error != null) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: colorScheme.errorContainer,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Icon(Icons.error_outline, color: colorScheme.error),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      _error!,
                      style: TextStyle(color: colorScheme.onErrorContainer),
                    ),
                  ),
                ],
              ),
            ),
          ],

          // Capture button
          const SizedBox(height: 24),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: _isCapturing ? null : () => Navigator.pop(context),
                  child: const Text('Cancel'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                flex: 2,
                child: FilledButton.icon(
                  onPressed: isConnected && !_isCapturing ? _capture : null,
                  icon: _isCapturing
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.save_alt),
                  label: Text(_isCapturing
                      ? 'Capturing...'
                      : _quickCapture
                          ? 'Quick Capture'
                          : 'Capture'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
        ],
      ),
    );
  }

  Widget _buildModelDropdown() {
    if (_loadingModels) {
      return const Center(child: LinearProgressIndicator());
    }

    final models = _models?.models ?? [];

    return DropdownButtonFormField<String>(
      value: _selectedModel,
      decoration: const InputDecoration(
        labelText: 'AI Model',
        border: OutlineInputBorder(),
        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      ),
      items: [
        const DropdownMenuItem(
          value: null,
          child: Text('Default'),
        ),
        ...models.map((model) => DropdownMenuItem(
              value: model.id,
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      model.shortName,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (model.statsString.isNotEmpty)
                    Text(
                      model.statsString,
                      style: TextStyle(
                        fontSize: 10,
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                ],
              ),
            )),
      ],
      onChanged: (value) => setState(() => _selectedModel = value),
    );
  }

  Widget _buildSubjectDropdown() {
    if (_loadingSubjects) {
      return const Center(child: LinearProgressIndicator());
    }

    final subjects = _subjects?.subjects ?? [];

    return DropdownButtonFormField<String>(
      value: _selectedSubject,
      decoration: const InputDecoration(
        labelText: 'Research Subject (optional)',
        border: OutlineInputBorder(),
        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      ),
      items: [
        const DropdownMenuItem(
          value: null,
          child: Text('None'),
        ),
        DropdownMenuItem(
          value: '__new__',
          child: Row(
            children: [
              Icon(Icons.add, size: 18),
              const SizedBox(width: 8),
              const Text('Create New Subject'),
            ],
          ),
        ),
        ...subjects.map((subject) => DropdownMenuItem(
              value: subject.name,
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      subject.displayName,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (subject.badges.isNotEmpty)
                    Text(
                      subject.badges.first,
                      style: TextStyle(
                        fontSize: 10,
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                ],
              ),
            )),
      ],
      onChanged: (value) {
        if (value == '__new__') {
          _createSubject();
        } else {
          setState(() => _selectedSubject = value);
        }
      },
    );
  }
}
