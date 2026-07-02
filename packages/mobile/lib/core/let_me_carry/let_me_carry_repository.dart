import 'dart:convert';

import 'package:app/core/api/api_client.dart';
import 'package:app/core/let_me_carry/let_me_carry_models.dart';
import 'package:dio/dio.dart';

/// Streams chat replies from the let_me_carry SSE endpoint.
class LetMeCarryRepository {
  LetMeCarryRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  /// Sends [message]; yields [LetMeCarryDelta]s as the reply streams.
  ///
  /// Pass the [threadId] returned by the previous turn's final event to keep
  /// the conversation threaded. Pass a [cancelToken] to abort the turn
  /// mid-stream (the model run is torn down server-side on disconnect).
  Stream<LetMeCarryDelta> streamChat({
    required String message,
    String? threadId,
    CancelToken? cancelToken,
  }) async* {
    final response = await _apiClient.dio.post<ResponseBody>(
      '/v1/let_me_carry/chat',
      data: {'message': message, if (threadId != null) 'thread_id': threadId},
      cancelToken: cancelToken,
      options: Options(
        responseType: ResponseType.stream,
        // Inter-chunk timeout. Use the longer deep-recap budget so slow
        // tool/research turns aren't aborted mid-stream.
        receiveTimeout: deepRecapReceiveTimeout,
      ),
    );

    final lines = response.data!.stream
        .cast<List<int>>()
        .transform(utf8.decoder)
        .transform(const LineSplitter());

    await for (final line in lines) {
      final trimmed = line.trim();
      if (!trimmed.startsWith('data:')) continue;
      final payload = trimmed.substring('data:'.length).trim();
      if (payload.isEmpty) continue;
      final json = jsonDecode(payload) as Map<String, dynamic>;
      yield LetMeCarryDelta.fromJson(json);
    }
  }
}
