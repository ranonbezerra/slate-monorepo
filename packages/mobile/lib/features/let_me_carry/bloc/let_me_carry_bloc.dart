import 'package:app/core/auth/email_verification.dart';
import 'package:app/core/let_me_carry/let_me_carry_models.dart';
import 'package:app/core/let_me_carry/let_me_carry_repository.dart';
import 'package:bloc/bloc.dart';
import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';

part 'let_me_carry_event.dart';
part 'let_me_carry_state.dart';

const _fallbackError = 'Sorry, something went wrong. Please try again.';

class LetMeCarryBloc extends Bloc<LetMeCarryEvent, LetMeCarryState> {
  LetMeCarryBloc({required LetMeCarryRepository letMeCarryRepository})
    : _letMeCarryRepository = letMeCarryRepository,
      super(const LetMeCarryState()) {
    on<SendLetMeCarryMessage>(_onSendMessage);
    on<CancelLetMeCarryStream>(_onCancel);
  }

  final LetMeCarryRepository _letMeCarryRepository;
  CancelToken? _cancelToken;

  Future<void> _onSendMessage(
    SendLetMeCarryMessage event,
    Emitter<LetMeCarryState> emit,
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
        status: LetMeCarryStatus.streaming,
        clearActiveTool: true,
      ),
    );

    final cancelToken = CancelToken();
    _cancelToken = cancelToken;
    final buffer = StringBuffer();
    Recommendation? recommendation;
    try {
      final stream = _letMeCarryRepository.streamChat(
        message: text,
        threadId: state.threadId,
        cancelToken: cancelToken,
      );
      var failed = false;
      await for (final delta in stream) {
        if (delta.error != null) {
          failed = true;
          emit(
            state.copyWith(
              messages: _withLastAssistant(delta.error!),
              status: LetMeCarryStatus.error,
              errorMessage: delta.error,
              clearActiveTool: true,
            ),
          );
          // Stop here so the trailing done event can't clear the error.
          break;
        }
        if (delta.token != null) {
          buffer.write(delta.token);
          emit(
            state.copyWith(
              messages: _withLastAssistant(buffer.toString(), recommendation),
            ),
          );
        }
        if (delta.tool != null) {
          emit(
            delta.phase == 'end'
                ? state.copyWith(clearActiveTool: true)
                : state.copyWith(activeTool: delta.tool),
          );
        }
        if (delta.recommendation != null) {
          recommendation = delta.recommendation;
          emit(
            state.copyWith(
              messages: _withLastAssistant(buffer.toString(), recommendation),
            ),
          );
        }
        if (delta.degrade != null) {
          buffer
            ..write('\n\n')
            ..write(delta.degrade);
          emit(
            state.copyWith(
              messages: _withLastAssistant(buffer.toString(), recommendation),
            ),
          );
        }
        if (delta.done && delta.threadId != null) {
          emit(state.copyWith(threadId: delta.threadId));
        }
      }
      if (!failed) {
        emit(
          state.copyWith(status: LetMeCarryStatus.idle, clearActiveTool: true),
        );
      }
    } on DioException catch (error) {
      if (CancelToken.isCancel(error)) {
        // User cancelled: keep the partial reply, just stop streaming.
        emit(
          state.copyWith(status: LetMeCarryStatus.idle, clearActiveTool: true),
        );
      } else if (EmailVerification.isUnverifiedError(error)) {
        // let_me_carry is cost-bearing; 403 until email is verified.
        _emitError(emit, message: EmailVerification.friendlyMessage);
      } else {
        _emitError(emit);
      }
    } on Exception {
      _emitError(emit);
    } finally {
      _cancelToken = null;
    }
  }

  void _onCancel(CancelLetMeCarryStream event, Emitter<LetMeCarryState> emit) {
    // Aborts the dio request; the send handler catches the cancellation and
    // settles the state (keeping the partial reply).
    _cancelToken?.cancel();
  }

  /// Replaces the trailing assistant placeholder with [text] and an optional
  /// validated [recommendation].
  List<ChatMessage> _withLastAssistant(
    String text, [
    Recommendation? recommendation,
  ]) {
    final messages = [...state.messages];
    messages[messages.length - 1] = ChatMessage(
      role: ChatRole.assistant,
      text: text,
      recommendation: recommendation,
    );
    return messages;
  }

  void _emitError(Emitter<LetMeCarryState> emit, {String? message}) {
    final text = message ?? _fallbackError;
    emit(
      state.copyWith(
        messages: _withLastAssistant(text),
        status: LetMeCarryStatus.error,
        errorMessage: text,
        clearActiveTool: true,
      ),
    );
  }
}
