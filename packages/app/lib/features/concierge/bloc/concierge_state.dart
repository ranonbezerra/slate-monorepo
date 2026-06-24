part of 'concierge_bloc.dart';

enum ConciergeStatus { initial, streaming, idle, error }

final class ConciergeState extends Equatable {
  const ConciergeState({
    this.messages = const [],
    this.status = ConciergeStatus.initial,
    this.threadId,
    this.errorMessage,
  });

  final List<ChatMessage> messages;
  final ConciergeStatus status;
  final String? threadId;
  final String? errorMessage;

  bool get isStreaming => status == ConciergeStatus.streaming;

  ConciergeState copyWith({
    List<ChatMessage>? messages,
    ConciergeStatus? status,
    String? threadId,
    String? errorMessage,
  }) {
    return ConciergeState(
      messages: messages ?? this.messages,
      status: status ?? this.status,
      threadId: threadId ?? this.threadId,
      errorMessage: errorMessage,
    );
  }

  @override
  List<Object?> get props => [messages, status, threadId, errorMessage];
}
