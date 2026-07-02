part of 'let_me_carry_bloc.dart';

sealed class LetMeCarryEvent extends Equatable {
  const LetMeCarryEvent();

  @override
  List<Object?> get props => [];
}

/// Send a user message and stream the LetMeCarry's guarded reply.
final class SendLetMeCarryMessage extends LetMeCarryEvent {
  const SendLetMeCarryMessage(this.message);

  final String message;

  @override
  List<Object?> get props => [message];
}

/// Cancel the in-flight turn mid-stream, keeping the partial reply.
final class CancelLetMeCarryStream extends LetMeCarryEvent {
  const CancelLetMeCarryStream();
}
