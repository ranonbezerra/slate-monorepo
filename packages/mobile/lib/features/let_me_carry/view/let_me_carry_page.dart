import 'package:app/core/let_me_carry/let_me_carry_models.dart';
import 'package:app/core/theme/slate_theme.dart';
import 'package:app/features/let_me_carry/bloc/let_me_carry_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

/// Friendly labels for the tool affordance shown while the agent works.
const _toolLabels = {
  'search_library': 'searching your library',
  'get_play_session_history': 'recalling your last session',
  'get_play_stats': 'checking your stats',
  'estimate_session_fit': 'sizing up the session',
  'start_play_session': 'starting your session',
  'generate_recap': 'writing a recap',
  'submit_retroactive_wrap_up': 'logging your session',
  'set_status': 'updating your library',
};

/// Conversational chat with the let_me_carry (Epic 11).
class LetMeCarryPage extends StatefulWidget {
  const LetMeCarryPage({super.key});

  @override
  State<LetMeCarryPage> createState() => _LetMeCarryPageState();
}

class _LetMeCarryPageState extends State<LetMeCarryPage> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _send() {
    final text = _controller.text.trim();
    final isStreaming = context.read<LetMeCarryBloc>().state.isStreaming;
    if (text.isEmpty || isStreaming) return;
    context.read<LetMeCarryBloc>().add(SendLetMeCarryMessage(text));
    _controller.clear();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('let_me_carry')),
      body: Column(
        children: [
          Expanded(
            child: BlocConsumer<LetMeCarryBloc, LetMeCarryState>(
              listener: (context, state) => _scrollToBottom(),
              builder: (context, state) {
                if (state.messages.isEmpty) {
                  return const _EmptyState();
                }
                return ListView.builder(
                  controller: _scrollController,
                  padding: const EdgeInsets.all(16),
                  itemCount: state.messages.length,
                  itemBuilder: (context, index) =>
                      _MessageBubble(message: state.messages[index]),
                );
              },
            ),
          ),
          const _ToolActivity(),
          _Composer(controller: _controller, onSend: _send),
        ],
      ),
    );
  }
}

/// A small "🔎 searching your library…" affordance shown while a tool runs.
class _ToolActivity extends StatelessWidget {
  const _ToolActivity();

  @override
  Widget build(BuildContext context) {
    final tool = context.select<LetMeCarryBloc, String?>(
      (bloc) => bloc.state.activeTool,
    );
    if (tool == null) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Row(
        children: [
          const SizedBox(
            width: 14,
            height: 14,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
          const SizedBox(width: 8),
          Text(
            '${_toolLabels[tool] ?? tool}…',
            style: const TextStyle(color: SlateColors.textMuted, fontSize: 12),
          ),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Padding(
        padding: EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.auto_awesome, size: 36, color: SlateColors.coral),
            SizedBox(height: 12),
            Text(
              'What should you play tonight?',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            SizedBox(height: 6),
            Text(
              'Try “I have 30 minutes and want something chill” or '
              '“What was I doing in my last RPG?”',
              textAlign: TextAlign.center,
              style: TextStyle(color: SlateColors.textMuted),
            ),
          ],
        ),
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message});

  final ChatMessage message;

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == ChatRole.user;
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.8,
        ),
        decoration: BoxDecoration(
          color: isUser ? SlateColors.coralDeep : SlateColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: SlateColors.line),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            if (message.text.isNotEmpty)
              Text(message.text)
            else if (message.recommendation == null)
              const Text('…'),
            if (message.recommendation != null) ...[
              const SizedBox(height: 8),
              FilledButton.icon(
                // Open the recap-choice flow for the recommended game,
                // mirroring the library "Start session" entry point.
                onPressed: () => context.push(
                  '/play-sessions/recap?entry=${message.recommendation!.id}',
                ),
                icon: const Icon(Icons.play_arrow, size: 18),
                label: Text('Play ${message.recommendation!.title}'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _Composer extends StatelessWidget {
  const _Composer({required this.controller, required this.onSend});

  final TextEditingController controller;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    final isStreaming = context.select<LetMeCarryBloc, bool>(
      (bloc) => bloc.state.isStreaming,
    );
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: controller,
                enabled: !isStreaming,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => onSend(),
                decoration: const InputDecoration(
                  hintText: 'Ask let_me_carry…',
                ),
              ),
            ),
            const SizedBox(width: 8),
            if (isStreaming)
              IconButton(
                onPressed: () => context.read<LetMeCarryBloc>().add(
                  const CancelLetMeCarryStream(),
                ),
                icon: const Icon(Icons.stop),
                color: SlateColors.coral,
                tooltip: 'Stop',
              )
            else
              IconButton(
                onPressed: onSend,
                icon: const Icon(Icons.send),
                color: SlateColors.coral,
                tooltip: 'Send',
              ),
          ],
        ),
      ),
    );
  }
}
