part of 'let_me_carry_bloc.dart';

enum LetMeCarryStatus { initial, streaming, idle, error }

final class LetMeCarryState extends Equatable {
  const LetMeCarryState({
    this.messages = const [],
    this.status = LetMeCarryStatus.initial,
    this.threadId,
    this.errorMessage,
    this.activeTool,
  });

  final List<ChatMessage> messages;
  final LetMeCarryStatus status;
  final String? threadId;
  final String? errorMessage;

  /// The tool the agent is currently running, shown as an affordance (Epic 16).
  final String? activeTool;

  bool get isStreaming => status == LetMeCarryStatus.streaming;

  LetMeCarryState copyWith({
    List<ChatMessage>? messages,
    LetMeCarryStatus? status,
    String? threadId,
    String? errorMessage,
    String? activeTool,
    bool clearActiveTool = false,
  }) {
    return LetMeCarryState(
      messages: messages ?? this.messages,
      status: status ?? this.status,
      threadId: threadId ?? this.threadId,
      errorMessage: errorMessage,
      activeTool: clearActiveTool ? null : (activeTool ?? this.activeTool),
    );
  }

  @override
  List<Object?> get props => [
    messages,
    status,
    threadId,
    errorMessage,
    activeTool,
  ];
}
