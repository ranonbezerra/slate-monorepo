import 'package:app/core/let_me_carry/let_me_carry_models.dart';
import 'package:app/features/let_me_carry/bloc/let_me_carry_bloc.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('LetMeCarryEvent', () {
    test('SendLetMeCarryMessage supports value equality and props', () {
      const a = SendLetMeCarryMessage('what should I play?');
      const b = SendLetMeCarryMessage('what should I play?');
      expect(a, b);
      expect(a.props, ['what should I play?']);
      expect(a, isNot(const SendLetMeCarryMessage('other')));
    });
  });

  group('LetMeCarryState', () {
    const message = ChatMessage(role: ChatRole.user, text: 'hi');

    test('default state has expected values', () {
      const state = LetMeCarryState();
      expect(state.messages, isEmpty);
      expect(state.status, LetMeCarryStatus.initial);
      expect(state.threadId, isNull);
      expect(state.errorMessage, isNull);
      expect(state.isStreaming, false);
    });

    test('supports value equality and props', () {
      const a = LetMeCarryState(
        messages: [message],
        status: LetMeCarryStatus.streaming,
        threadId: 't-1',
        errorMessage: 'oops',
      );
      const b = LetMeCarryState(
        messages: [message],
        status: LetMeCarryStatus.streaming,
        threadId: 't-1',
        errorMessage: 'oops',
      );
      expect(a, b);
      expect(a.isStreaming, true);
      expect(a.props, [
        [message],
        LetMeCarryStatus.streaming,
        't-1',
        'oops',
        null,
      ]);
    });

    test('copyWith sets and clears the active tool', () {
      const base = LetMeCarryState();
      final running = base.copyWith(activeTool: 'search_library');
      expect(running.activeTool, 'search_library');
      // A plain copyWith keeps it; clearActiveTool resets it.
      expect(running.copyWith(threadId: 't').activeTool, 'search_library');
      expect(running.copyWith(clearActiveTool: true).activeTool, isNull);
    });

    test('copyWith updates provided fields and clears errorMessage', () {
      const base = LetMeCarryState(
        status: LetMeCarryStatus.error,
        errorMessage: 'boom',
        threadId: 't-1',
      );
      final updated = base.copyWith(
        status: LetMeCarryStatus.idle,
        messages: const [message],
      );
      expect(updated.status, LetMeCarryStatus.idle);
      expect(updated.messages, [message]);
      expect(updated.threadId, 't-1');
      // errorMessage is always reset by copyWith.
      expect(updated.errorMessage, isNull);
    });
  });
}
