import 'dart:convert';
import 'dart:typed_data';

import 'package:app/core/api/api_client.dart';
import 'package:app/core/let_me_carry/let_me_carry_models.dart';
import 'package:app/core/let_me_carry/let_me_carry_repository.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockApiClient extends Mock implements ApiClient {}

class MockDio extends Mock implements Dio {}

ResponseBody _sseBody(List<String> events) {
  final chunks = events.map((e) => Uint8List.fromList(utf8.encode(e)));
  return ResponseBody(Stream.fromIterable(chunks), 200);
}

void main() {
  late MockApiClient apiClient;
  late MockDio dio;
  late LetMeCarryRepository repository;

  setUp(() {
    apiClient = MockApiClient();
    dio = MockDio();
    when(() => apiClient.dio).thenReturn(dio);
    repository = LetMeCarryRepository(apiClient: apiClient);
  });

  test('parses SSE delta and done events into LetMeCarryDeltas', () async {
    when(
      () => dio.post<ResponseBody>(
        any(),
        data: any(named: 'data'),
        cancelToken: any(named: 'cancelToken'),
        options: any(named: 'options'),
      ),
    ).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: '/v1/let_me_carry/chat'),
        data: _sseBody([
          'data: {"token": "Play "}\n\n',
          'data: {"token": "Hades."}\n\n',
          'data: {"done": true, "thread_id": "t1"}\n\n',
        ]),
      ),
    );

    final deltas = await repository.streamChat(message: 'hi').toList();

    expect(deltas, [
      const LetMeCarryDelta(token: 'Play '),
      const LetMeCarryDelta(token: 'Hades.'),
      const LetMeCarryDelta(done: true, threadId: 't1'),
    ]);
  });

  test('skips blank and non-data lines', () async {
    when(
      () => dio.post<ResponseBody>(
        any(),
        data: any(named: 'data'),
        cancelToken: any(named: 'cancelToken'),
        options: any(named: 'options'),
      ),
    ).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: '/v1/let_me_carry/chat'),
        data: _sseBody([': keep-alive\n', '\n', 'data: {"token": "Hi"}\n\n']),
      ),
    );

    final deltas = await repository.streamChat(message: 'hi').toList();

    expect(deltas, [const LetMeCarryDelta(token: 'Hi')]);
  });
}
