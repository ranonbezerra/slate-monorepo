part of 'play_session_bloc.dart';

sealed class PlaySessionEvent extends Equatable {
  const PlaySessionEvent();

  @override
  List<Object?> get props => [];
}

/// Dispatched to load the playSession history list.
final class LoadPlaySessions extends PlaySessionEvent {
  const LoadPlaySessions({this.limit, this.offset});

  final int? limit;
  final int? offset;

  @override
  List<Object?> get props => [limit, offset];
}

/// Dispatched to load the next page of playSessions.
final class LoadMorePlaySessions extends PlaySessionEvent {
  const LoadMorePlaySessions();
}

/// Dispatched to load the currently active playSession.
final class LoadActivePlaySession extends PlaySessionEvent {
  const LoadActivePlaySession();
}

/// Dispatched to preview a recap before starting a playSession.
final class PreviewRecap extends PlaySessionEvent {
  const PreviewRecap({
    required this.libraryEntryPublicId,
    this.positionOverride,
    this.mode = 'quick',
  });

  final String libraryEntryPublicId;
  final String? positionOverride;

  /// Recap mode: `'quick'` (single-shot) or `'deep'` (web-researched).
  final String mode;

  @override
  List<Object?> get props => [libraryEntryPublicId, positionOverride, mode];
}

/// Dispatched to cancel an in-flight deep recap request.
final class CancelDeepRecap extends PlaySessionEvent {
  const CancelDeepRecap({required this.libraryEntryPublicId});

  final String libraryEntryPublicId;

  @override
  List<Object?> get props => [libraryEntryPublicId];
}

/// Dispatched to start a new playSession.
final class StartPlaySession extends PlaySessionEvent {
  const StartPlaySession({
    required this.libraryEntryPublicId,
    this.recapText,
    this.skipRecap = false,
  });

  final String libraryEntryPublicId;
  final String? recapText;

  /// Start with no recap at all (the "just play" path).
  final bool skipRecap;

  @override
  List<Object?> get props => [libraryEntryPublicId, recapText, skipRecap];
}

/// Dispatched to submit a debrief for a playSession.
final class SubmitDebrief extends PlaySessionEvent {
  const SubmitDebrief({required this.publicId, required this.debriefText});

  final String publicId;
  final String debriefText;

  @override
  List<Object?> get props => [publicId, debriefText];
}

/// Dispatched to end a playSession.
final class EndPlaySession extends PlaySessionEvent {
  const EndPlaySession({required this.publicId, this.endedVia = 'paused_app'});

  final String publicId;
  final String endedVia;

  @override
  List<Object?> get props => [publicId, endedVia];
}

/// Dispatched to submit a retroactive debrief for a library entry.
final class SubmitRetroactiveDebrief extends PlaySessionEvent {
  const SubmitRetroactiveDebrief({
    required this.libraryEntryPublicId,
    required this.debriefText,
  });

  final String libraryEntryPublicId;
  final String debriefText;

  @override
  List<Object?> get props => [libraryEntryPublicId, debriefText];
}

/// Dispatched to regenerate the recap for an existing playSession.
final class RegenerateRecap extends PlaySessionEvent {
  const RegenerateRecap({required this.publicId, this.currentPosition});

  final String publicId;
  final String? currentPosition;

  @override
  List<Object?> get props => [publicId, currentPosition];
}
