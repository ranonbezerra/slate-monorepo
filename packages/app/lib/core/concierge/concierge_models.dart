import 'package:equatable/equatable.dart';

/// Who authored a chat message.
enum ChatRole { user, assistant }

/// A single message in a Concierge conversation.
class ChatMessage extends Equatable {
  const ChatMessage({required this.role, required this.text});

  final ChatRole role;
  final String text;

  ChatMessage copyWith({String? text}) {
    return ChatMessage(role: role, text: text ?? this.text);
  }

  @override
  List<Object?> get props => [role, text];
}

/// One Server-Sent Event from `POST /v1/concierge/chat`.
///
/// While the guarded reply streams, events carry a [delta]; the final event
/// has [done] set and supplies the [threadId] for the next turn.
class ConciergeDelta extends Equatable {
  const ConciergeDelta({
    this.delta,
    this.error,
    this.done = false,
    this.threadId,
  });

  factory ConciergeDelta.fromJson(Map<String, dynamic> json) {
    return ConciergeDelta(
      delta: json['delta'] as String?,
      error: json['error'] as String?,
      done: json['done'] as bool? ?? false,
      threadId: json['thread_id'] as String?,
    );
  }

  final String? delta;

  /// Set when the server reports a failure mid-stream (e.g. model unavailable).
  final String? error;
  final bool done;
  final String? threadId;

  @override
  List<Object?> get props => [delta, error, done, threadId];
}
