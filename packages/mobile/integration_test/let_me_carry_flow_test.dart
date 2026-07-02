import 'dart:convert';
import 'dart:typed_data';

import 'package:app/core/api/api_client.dart';
import 'package:app/core/auth/auth_token_store.dart';
import 'package:app/core/let_me_carry/let_me_carry_repository.dart';
import 'package:app/core/theme/slate_theme.dart';
import 'package:app/features/let_me_carry/bloc/let_me_carry_bloc.dart';
import 'package:app/features/let_me_carry/view/let_me_carry_page.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

/// Headless integration test for the let_me_carry.
///
/// Unlike the widget test (which mocks [LetMeCarryRepository]), this drives the
/// *real* stack — [LetMeCarryRepository] → [ApiClient]'s Dio → SSE line parsing
/// → [LetMeCarryBloc] → [LetMeCarryPage] — mocking only at the network adapter.
/// It validates that the on-the-wire SSE format the API emits is decoded and
/// rendered end to end, including the validated-recommendation Play CTA.
///
/// Run headless: `fvm flutter test integration_test/let_me_carry_flow_test.dart`.
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('streams a guarded reply and offers a Play CTA', (tester) async {
    final dio = Dio(BaseOptions(baseUrl: 'http://localhost:8100'))
      ..httpClientAdapter = _SseMockAdapter();
    final apiClient = ApiClient(tokenStore: AuthTokenStore(), dio: dio);
    final repository = LetMeCarryRepository(apiClient: apiClient);

    await tester.pumpWidget(
      MaterialApp(
        theme: SlateTheme.dark,
        home: BlocProvider(
          create: (_) => LetMeCarryBloc(letMeCarryRepository: repository),
          child: const LetMeCarryPage(),
        ),
      ),
    );

    expect(find.text('What should you play tonight?'), findsOneWidget);

    await tester.enterText(
      find.byType(TextField),
      'what should I play tonight?',
    );
    await tester.testTextInput.receiveAction(TextInputAction.send);
    await tester.pumpAndSettle();

    // The streamed prose and the validated recommendation CTA both render;
    // the raw `RECOMMEND:` marker is withheld by the server-side gate.
    expect(find.text('Give Hollow Knight a go tonight.'), findsOneWidget);
    expect(find.text('Play Hollow Knight'), findsOneWidget);
  });
}

/// A Dio adapter that replies to the let_me_carry endpoint with a canned SSE
/// stream matching the API's on-the-wire event format, and `{}` to anything
/// else so an unexpected call never hangs the test.
class _SseMockAdapter implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    if (options.path == '/v1/let_me_carry/chat') {
      const rec = '{"id": "le-hollow-knight", "title": "Hollow Knight"}';
      final sse = [
        'data: {"tool": "search_library", "phase": "start"}',
        'data: {"tool": "search_library", "phase": "end"}',
        'data: {"token": "Give Hollow Knight a go tonight."}',
        'data: {"recommendation": $rec}',
        'data: {"done": true, "thread_id": "t-it"}',
      ].map((line) => '$line\n\n').join();
      return ResponseBody(
        Stream<Uint8List>.fromIterable([Uint8List.fromList(utf8.encode(sse))]),
        200,
        headers: {
          Headers.contentTypeHeader: ['text/event-stream'],
        },
      );
    }
    return ResponseBody.fromString(
      '{}',
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}
