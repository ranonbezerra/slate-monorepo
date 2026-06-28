import 'package:app/core/auth/email_verification.dart';
import 'package:app/core/play_session/play_session_models.dart';
import 'package:app/core/play_session/play_session_repository.dart';
import 'package:bloc/bloc.dart';
import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';

part 'play_session_event.dart';
part 'play_session_state.dart';

const _pageSize = 10;

class PlaySessionBloc extends Bloc<PlaySessionEvent, PlaySessionState> {
  PlaySessionBloc({required PlaySessionRepository playSessionRepository})
    : _playSessionRepository = playSessionRepository,
      super(const PlaySessionInitial()) {
    on<LoadPlaySessions>(_onLoadPlaySessions);
    on<LoadMorePlaySessions>(_onLoadMorePlaySessions);
    on<LoadActivePlaySession>(_onLoadActivePlaySession);
    on<PreviewBriefing>(_onPreviewBriefing);
    on<CancelDeepBriefing>(_onCancelDeepBriefing);
    on<StartPlaySession>(_onStartPlaySession);
    on<SubmitDebrief>(_onSubmitDebrief);
    on<EndPlaySession>(_onEndPlaySession);
    on<SubmitRetroactiveDebrief>(_onSubmitRetroactiveDebrief);
    on<RegenerateBriefing>(_onRegenerateBriefing);
  }

  final PlaySessionRepository _playSessionRepository;

  /// Active cancel token for an in-flight deep briefing request, if any.
  CancelToken? _deepCancelToken;

  Future<void> _onLoadPlaySessions(
    LoadPlaySessions event,
    Emitter<PlaySessionState> emit,
  ) async {
    emit(const PlaySessionLoading());

    try {
      final response = await _playSessionRepository.listPlaySessions(
        limit: event.limit ?? _pageSize,
        offset: event.offset ?? 0,
      );

      emit(
        PlaySessionListLoaded(
          playSessions: response.items,
          total: response.total,
        ),
      );
    } on DioException catch (e) {
      emit(PlaySessionError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(PlaySessionError(message: e.toString()));
    }
  }

  Future<void> _onLoadMorePlaySessions(
    LoadMorePlaySessions event,
    Emitter<PlaySessionState> emit,
  ) async {
    final currentState = state;
    if (currentState is! PlaySessionListLoaded || !currentState.hasMore) return;
    if (currentState.isLoadingMore) return;

    emit(currentState.copyWith(isLoadingMore: true));

    try {
      final response = await _playSessionRepository.listPlaySessions(
        limit: _pageSize,
        offset: currentState.playSessions.length,
      );

      emit(
        PlaySessionListLoaded(
          playSessions: [...currentState.playSessions, ...response.items],
          total: response.total,
        ),
      );
    } on DioException catch (e) {
      // Keep the loaded list visible; surface the error inline.
      emit(
        currentState.copyWith(
          isLoadingMore: false,
          loadMoreError: _extractErrorMessage(e),
        ),
      );
    } on Exception catch (e) {
      emit(
        currentState.copyWith(
          isLoadingMore: false,
          loadMoreError: e.toString(),
        ),
      );
    }
  }

  Future<void> _onLoadActivePlaySession(
    LoadActivePlaySession event,
    Emitter<PlaySessionState> emit,
  ) async {
    emit(const PlaySessionLoading());

    try {
      final playSession = await _playSessionRepository.getActivePlaySession();
      emit(ActivePlaySessionLoaded(playSession: playSession));
    } on DioException catch (e) {
      emit(PlaySessionError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(PlaySessionError(message: e.toString()));
    }
  }

  Future<void> _onPreviewBriefing(
    PreviewBriefing event,
    Emitter<PlaySessionState> emit,
  ) async {
    final isDeep = event.mode == 'deep';
    if (isDeep) {
      _deepCancelToken = CancelToken();
      emit(const DeepBriefingLoading());
    } else {
      emit(const PlaySessionLoading());
    }

    try {
      final preview = await _playSessionRepository.previewBriefing(
        event.libraryEntryPublicId,
        positionOverride: event.positionOverride,
        mode: event.mode,
        cancelToken: isDeep ? _deepCancelToken : null,
      );
      emit(BriefingPreviewLoaded(preview: preview, isDeep: isDeep));
    } on DioException catch (e) {
      if (CancelToken.isCancel(e)) {
        // User cancelled the deep request -- fall back to the quick briefing.
        await _emitQuickPreview(event.libraryEntryPublicId, emit);
        return;
      }
      emit(PlaySessionError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(PlaySessionError(message: e.toString()));
    } finally {
      if (isDeep) _deepCancelToken = null;
    }
  }

  Future<void> _onCancelDeepBriefing(
    CancelDeepBriefing event,
    Emitter<PlaySessionState> emit,
  ) async {
    _deepCancelToken?.cancel('cancelled_by_user');
  }

  Future<void> _emitQuickPreview(
    String libraryEntryPublicId,
    Emitter<PlaySessionState> emit,
  ) async {
    try {
      final preview = await _playSessionRepository.previewBriefing(
        libraryEntryPublicId,
      );
      emit(BriefingPreviewLoaded(preview: preview));
    } on DioException catch (e) {
      emit(PlaySessionError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(PlaySessionError(message: e.toString()));
    }
  }

  Future<void> _onStartPlaySession(
    StartPlaySession event,
    Emitter<PlaySessionState> emit,
  ) async {
    emit(const PlaySessionLoading());

    try {
      final playSession = await _playSessionRepository.startPlaySession(
        event.libraryEntryPublicId,
        briefingText: event.briefingText,
        skipBriefing: event.skipBriefing,
      );
      emit(PlaySessionStarted(playSession: playSession));
    } on DioException catch (e) {
      emit(PlaySessionError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(PlaySessionError(message: e.toString()));
    }
  }

  Future<void> _onSubmitDebrief(
    SubmitDebrief event,
    Emitter<PlaySessionState> emit,
  ) async {
    emit(const PlaySessionLoading());

    try {
      final playSession = await _playSessionRepository.submitDebrief(
        event.publicId,
        event.debriefText,
      );
      emit(PlaySessionEnded(playSession: playSession));
    } on DioException catch (e) {
      emit(PlaySessionError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(PlaySessionError(message: e.toString()));
    }
  }

  Future<void> _onEndPlaySession(
    EndPlaySession event,
    Emitter<PlaySessionState> emit,
  ) async {
    emit(const PlaySessionLoading());

    try {
      final playSession = await _playSessionRepository.endPlaySession(
        event.publicId,
        endedVia: event.endedVia,
      );
      emit(PlaySessionEnded(playSession: playSession));
    } on DioException catch (e) {
      emit(PlaySessionError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(PlaySessionError(message: e.toString()));
    }
  }

  Future<void> _onSubmitRetroactiveDebrief(
    SubmitRetroactiveDebrief event,
    Emitter<PlaySessionState> emit,
  ) async {
    emit(const PlaySessionLoading());

    try {
      final preview = await _playSessionRepository.submitRetroactiveDebrief(
        event.libraryEntryPublicId,
        event.debriefText,
      );
      emit(BriefingPreviewLoaded(preview: preview));
    } on DioException catch (e) {
      emit(PlaySessionError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(PlaySessionError(message: e.toString()));
    }
  }

  Future<void> _onRegenerateBriefing(
    RegenerateBriefing event,
    Emitter<PlaySessionState> emit,
  ) async {
    emit(const PlaySessionLoading());

    try {
      final playSession = await _playSessionRepository.regenerateBriefing(
        event.publicId,
        currentPosition: event.currentPosition,
      );
      emit(PlaySessionStarted(playSession: playSession));
    } on DioException catch (e) {
      emit(PlaySessionError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(PlaySessionError(message: e.toString()));
    }
  }

  String _extractErrorMessage(DioException e) {
    // Briefing generation 403s until the email is verified; surface the
    // actionable verify prompt rather than the bare API detail.
    if (EmailVerification.isUnverifiedError(e)) {
      return EmailVerification.friendlyMessage;
    }
    final data = e.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is String) return detail;
    }
    return e.message ?? 'An unexpected error occurred.';
  }
}
