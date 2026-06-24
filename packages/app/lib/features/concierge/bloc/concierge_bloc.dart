import 'package:app/core/concierge/concierge_models.dart';
import 'package:app/core/concierge/concierge_repository.dart';
import 'package:bloc/bloc.dart';
import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';

part 'concierge_event.dart';
part 'concierge_state.dart';

const _fallbackError = 'Sorry, something went wrong. Please try again.';

class ConciergeBloc extends Bloc<ConciergeEvent, ConciergeState> {
  ConciergeBloc({required ConciergeRepository conciergeRepository})
    : _conciergeRepository = conciergeRepository,
      super(const ConciergeState()) {
    on<SendConciergeMessage>(_onSendMessage);
  }

  final ConciergeRepository _conciergeRepository;

  Future<void> _onSendMessage(
    SendConciergeMessage event,
    Emitter<ConciergeState> emit,
  ) async {
    final text = event.message.trim();
    if (text.isEmpty || state.isStreaming) return;

    // Append the user message + an empty assistant placeholder to fill in.
    emit(
      state.copyWith(
        messages: [
          ...state.messages,
          ChatMessage(role: ChatRole.user, text: text),
          const ChatMessage(role: ChatRole.assistant, text: ''),
        ],
        status: ConciergeStatus.streaming,
      ),
    );

    final buffer = StringBuffer();
    try {
      final stream = _conciergeRepository.streamChat(
        message: text,
        threadId: state.threadId,
      );
      var failed = false;
      await for (final delta in stream) {
        if (delta.error != null) {
          failed = true;
          emit(
            state.copyWith(
              messages: _withLastAssistant(delta.error!),
              status: ConciergeStatus.error,
              errorMessage: delta.error,
            ),
          );
          // Stop here so the trailing done event can't clear the error.
          break;
        }
        if (delta.delta != null) {
          buffer.write(delta.delta);
          emit(state.copyWith(messages: _withLastAssistant(buffer.toString())));
        }
        if (delta.done && delta.threadId != null) {
          emit(state.copyWith(threadId: delta.threadId));
        }
      }
      if (!failed) {
        emit(state.copyWith(status: ConciergeStatus.idle));
      }
    } on DioException {
      _emitError(emit);
    } on Exception {
      _emitError(emit);
    }
  }

  /// Replaces the trailing assistant placeholder with [text].
  List<ChatMessage> _withLastAssistant(String text) {
    final messages = [...state.messages];
    messages[messages.length - 1] = ChatMessage(
      role: ChatRole.assistant,
      text: text,
    );
    return messages;
  }

  void _emitError(Emitter<ConciergeState> emit) {
    emit(
      state.copyWith(
        messages: _withLastAssistant(_fallbackError),
        status: ConciergeStatus.error,
        errorMessage: _fallbackError,
      ),
    );
  }
}
