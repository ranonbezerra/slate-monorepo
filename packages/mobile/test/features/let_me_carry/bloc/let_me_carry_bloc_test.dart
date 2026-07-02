import 'package:app/core/let_me_carry/let_me_carry_models.dart';
import 'package:app/core/let_me_carry/let_me_carry_repository.dart';
import 'package:app/features/let_me_carry/bloc/let_me_carry_bloc.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockLetMeCarryRepository extends Mock implements LetMeCarryRepository {}

Stream<LetMeCarryDelta> _deltas(List<LetMeCarryDelta> items) async* {
  for (final item in items) {
    yield item;
  }
}

void main() {
  late MockLetMeCarryRepository repository;

  setUp(() {
    repository = MockLetMeCarryRepository();
  });

  LetMeCarryBloc buildBloc() =>
      LetMeCarryBloc(letMeCarryRepository: repository);

  group('LetMeCarryBloc', () {
    test('initial state is empty and idle', () {
      final bloc = buildBloc();
      expect(bloc.state.messages, isEmpty);
      expect(bloc.state.status, LetMeCarryStatus.initial);
      bloc.close();
    });

    blocTest<LetMeCarryBloc, LetMeCarryState>(
      'streams the reply, threads the id, and ends idle',
      setUp: () {
        when(
          () => repository.streamChat(
            message: any(named: 'message'),
            threadId: any(named: 'threadId'),
            cancelToken: any(named: 'cancelToken'),
          ),
        ).thenAnswer(
          (_) => _deltas(const [
            LetMeCarryDelta(token: 'Play '),
            LetMeCarryDelta(token: 'Hades.'),
            LetMeCarryDelta(done: true, threadId: 't1'),
          ]),
        );
      },
      build: buildBloc,
      act: (bloc) =>
          bloc.add(const SendLetMeCarryMessage('what should I play?')),
      verify: (bloc) {
        expect(bloc.state.status, LetMeCarryStatus.idle);
        expect(bloc.state.threadId, 't1');
        expect(bloc.state.messages, [
          const ChatMessage(role: ChatRole.user, text: 'what should I play?'),
          const ChatMessage(role: ChatRole.assistant, text: 'Play Hades.'),
        ]);
      },
    );

    blocTest<LetMeCarryBloc, LetMeCarryState>(
      'ignores blank messages',
      build: buildBloc,
      act: (bloc) => bloc.add(const SendLetMeCarryMessage('   ')),
      expect: () => const <LetMeCarryState>[],
      verify: (_) {
        verifyNever(
          () => repository.streamChat(
            message: any(named: 'message'),
            threadId: any(named: 'threadId'),
            cancelToken: any(named: 'cancelToken'),
          ),
        );
      },
    );

    blocTest<LetMeCarryBloc, LetMeCarryState>(
      'emits an error state when the stream fails',
      setUp: () {
        when(
          () => repository.streamChat(
            message: any(named: 'message'),
            threadId: any(named: 'threadId'),
            cancelToken: any(named: 'cancelToken'),
          ),
        ).thenThrow(
          DioException(
            requestOptions: RequestOptions(path: '/v1/let_me_carry/chat'),
          ),
        );
      },
      build: buildBloc,
      act: (bloc) => bloc.add(const SendLetMeCarryMessage('hello')),
      verify: (bloc) {
        expect(bloc.state.status, LetMeCarryStatus.error);
        expect(bloc.state.errorMessage, isNotNull);
        expect(bloc.state.messages.last.role, ChatRole.assistant);
        expect(bloc.state.messages.last.text, contains('something went wrong'));
      },
    );

    blocTest<LetMeCarryBloc, LetMeCarryState>(
      'surfaces a server error event as an error state',
      setUp: () {
        when(
          () => repository.streamChat(
            message: any(named: 'message'),
            threadId: any(named: 'threadId'),
            cancelToken: any(named: 'cancelToken'),
          ),
        ).thenAnswer(
          (_) => _deltas(const [
            LetMeCarryDelta(
              error: 'The let_me_carry is unavailable right now.',
            ),
            LetMeCarryDelta(done: true, threadId: 't1'),
          ]),
        );
      },
      build: buildBloc,
      act: (bloc) => bloc.add(const SendLetMeCarryMessage('hi')),
      verify: (bloc) {
        expect(bloc.state.status, LetMeCarryStatus.error);
        expect(bloc.state.errorMessage, contains('unavailable'));
        expect(bloc.state.messages.last.text, contains('unavailable'));
      },
    );

    blocTest<LetMeCarryBloc, LetMeCarryState>(
      'attaches a recommendation and surfaces tool activity',
      setUp: () {
        when(
          () => repository.streamChat(
            message: any(named: 'message'),
            threadId: any(named: 'threadId'),
            cancelToken: any(named: 'cancelToken'),
          ),
        ).thenAnswer(
          (_) => _deltas(const [
            LetMeCarryDelta(tool: 'search_library', phase: 'start'),
            LetMeCarryDelta(tool: 'search_library', phase: 'end'),
            LetMeCarryDelta(token: 'Give this a go.'),
            LetMeCarryDelta(
              recommendation: Recommendation(id: 'abc', title: 'Hades'),
            ),
            LetMeCarryDelta(done: true, threadId: 't1'),
          ]),
        );
      },
      build: buildBloc,
      act: (bloc) =>
          bloc.add(const SendLetMeCarryMessage('what should I play?')),
      verify: (bloc) {
        expect(bloc.state.status, LetMeCarryStatus.idle);
        expect(bloc.state.activeTool, isNull); // cleared once the turn ends
        final last = bloc.state.messages.last;
        expect(last.text, 'Give this a go.');
        expect(
          last.recommendation,
          const Recommendation(id: 'abc', title: 'Hades'),
        );
      },
    );

    blocTest<LetMeCarryBloc, LetMeCarryState>(
      'cancelling keeps the partial reply and settles idle',
      setUp: () {
        when(
          () => repository.streamChat(
            message: any(named: 'message'),
            threadId: any(named: 'threadId'),
            cancelToken: any(named: 'cancelToken'),
          ),
        ).thenThrow(
          DioException.requestCancelled(
            requestOptions: RequestOptions(path: '/v1/let_me_carry/chat'),
            reason: 'cancelled',
          ),
        );
      },
      build: buildBloc,
      act: (bloc) => bloc.add(const SendLetMeCarryMessage('hello')),
      verify: (bloc) {
        // A cancellation is not an error — no error state, partial kept.
        expect(bloc.state.status, LetMeCarryStatus.idle);
        expect(bloc.state.errorMessage, isNull);
      },
    );

    blocTest<LetMeCarryBloc, LetMeCarryState>(
      'threads the previous thread id into the next turn',
      setUp: () {
        when(
          () => repository.streamChat(
            message: any(named: 'message'),
            threadId: any(named: 'threadId'),
            cancelToken: any(named: 'cancelToken'),
          ),
        ).thenAnswer(
          (_) => _deltas(const [
            LetMeCarryDelta(done: true, threadId: 'thread-42'),
          ]),
        );
      },
      build: buildBloc,
      act: (bloc) async {
        bloc.add(const SendLetMeCarryMessage('first'));
        await bloc.stream.firstWhere((s) => s.status == LetMeCarryStatus.idle);
        bloc.add(const SendLetMeCarryMessage('second'));
        await bloc.stream.firstWhere(
          (s) => s.status == LetMeCarryStatus.idle && s.messages.length == 4,
        );
      },
      verify: (_) {
        verify(
          () => repository.streamChat(
            message: 'first',
            threadId: any(named: 'threadId', that: isNull),
            cancelToken: any(named: 'cancelToken'),
          ),
        ).called(1);
        verify(
          () => repository.streamChat(
            message: 'second',
            threadId: 'thread-42',
            cancelToken: any(named: 'cancelToken'),
          ),
        ).called(1);
      },
    );
  });
}
