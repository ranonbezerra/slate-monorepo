import 'package:app/core/api/api_client.dart';
import 'package:app/core/play_session/play_session_models.dart';
import 'package:dio/dio.dart';

final _llmOptions = Options(receiveTimeout: llmReceiveTimeout);
final _deepLlmOptions = Options(receiveTimeout: deepBriefingReceiveTimeout);

/// Provides high-level playSession operations backed by the API.
class PlaySessionRepository {
  PlaySessionRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  final ApiClient _apiClient;

  /// Previews a briefing for a library entry before starting a playSession.
  ///
  /// [mode] selects the quick single-shot briefing or the deep web-researched
  /// one. Deep mode uses a longer receive timeout and accepts a [cancelToken]
  /// so the user can abort the (slow) request.
  Future<BriefingPreview> previewBriefing(
    String libraryEntryPublicId, {
    String? positionOverride,
    String mode = 'quick',
    CancelToken? cancelToken,
  }) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/play-sessions/preview-briefing',
      data: {
        'library_entry_public_id': libraryEntryPublicId,
        'mode': mode,
        if (positionOverride != null) 'position_override': positionOverride,
      },
      options: mode == 'deep' ? _deepLlmOptions : _llmOptions,
      cancelToken: cancelToken,
    );
    return BriefingPreview.fromJson(response.data!);
  }

  /// Submits a retroactive debrief for a library entry.
  Future<BriefingPreview> submitRetroactiveDebrief(
    String libraryEntryPublicId,
    String debriefText,
  ) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/play-sessions/retroactive-debrief',
      data: {
        'library_entry_public_id': libraryEntryPublicId,
        'debrief_text': debriefText,
      },
    );
    return BriefingPreview.fromJson(response.data!);
  }

  /// Starts a new playSession for a library entry.
  ///
  /// Pass [skipBriefing] to start with no briefing at all (the "just play"
  /// path) — otherwise, with no [briefingText], the backend generates one.
  Future<PlaySession> startPlaySession(
    String libraryEntryPublicId, {
    String? briefingText,
    bool skipBriefing = false,
  }) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/play-sessions',
      data: {
        'library_entry_public_id': libraryEntryPublicId,
        if (briefingText != null) 'briefing_text': briefingText,
        if (skipBriefing) 'skip_briefing': true,
      },
    );
    return PlaySession.fromJson(response.data!);
  }

  /// Fetches the currently active playSession, or `null` if none exists.
  Future<PlaySession?> getActivePlaySession() async {
    try {
      final response = await _apiClient.dio.get<Map<String, dynamic>>(
        '/v1/play-sessions/active',
      );
      return PlaySession.fromJson(response.data!);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        return null;
      }
      rethrow;
    }
  }

  /// Fetches a single playSession by its public ID.
  Future<PlaySession> getPlaySession(String publicId) async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/v1/play-sessions/$publicId',
    );
    return PlaySession.fromJson(response.data!);
  }

  /// Lists the current user's play sessions.
  Future<PlaySessionListResponse> listPlaySessions({
    int limit = 50,
    int offset = 0,
  }) async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/v1/play-sessions',
      queryParameters: {'limit': limit, 'offset': offset},
    );
    return PlaySessionListResponse.fromJson(response.data!);
  }

  /// Submits a debrief for a playSession.
  Future<PlaySession> submitDebrief(String publicId, String debriefText) async {
    final response = await _apiClient.dio.patch<Map<String, dynamic>>(
      '/v1/play-sessions/$publicId/debrief',
      data: {'debrief_text': debriefText},
    );
    return PlaySession.fromJson(response.data!);
  }

  /// Ends a playSession with the given reason.
  Future<PlaySession> endPlaySession(
    String publicId, {
    String endedVia = 'paused_app',
  }) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/play-sessions/$publicId/end',
      data: {'ended_via': endedVia},
    );
    return PlaySession.fromJson(response.data!);
  }

  /// Regenerates the briefing for an existing playSession.
  Future<PlaySession> regenerateBriefing(
    String publicId, {
    String? currentPosition,
  }) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/play-sessions/$publicId/briefing/regenerate',
      data: {if (currentPosition != null) 'current_position': currentPosition},
      options: _llmOptions,
    );
    return PlaySession.fromJson(response.data!);
  }
}
